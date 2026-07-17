#!/usr/bin/env python3
"""Static contracts for pinned Docker and Netbird-backed Swarm bootstrap."""

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE = ROOT / "bootstrap" / "ansible"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(relative_path: str):
    path = ANSIBLE / relative_path
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text())


def task_named(tasks: list[dict], name: str) -> dict:
    return next((task for task in (tasks or []) if task.get("name") == name), {})


variables = load("group_vars/all.yml")
expected_packages = {
    "docker-ce": "5:29.6.1-1~ubuntu.24.04~noble",
    "docker-ce-cli": "5:29.6.1-1~ubuntu.24.04~noble",
    "containerd.io": "2.2.5-1~ubuntu.24.04~noble",
    "docker-buildx-plugin": "0.35.0-1~ubuntu.24.04~noble",
    "docker-compose-plugin": "5.3.1-1~ubuntu.24.04~noble",
}
actual_packages = {
    package["name"]: package["version"] for package in variables.get("docker_packages", [])
}
if actual_packages != expected_packages:
    fail("group_vars/all.yml must preserve every exact Docker package pin")

requirements = load("requirements.yml")
docker_collection = next(
    (
        collection
        for collection in requirements.get("collections", [])
        if collection.get("name") == "community.docker"
    ),
    {},
)
if not docker_collection.get("version"):
    fail("community.docker must have an exact version")

docker_tasks = load("roles/docker/tasks/main.yml")
install = task_named(docker_tasks, "Install pinned Docker Engine packages")
if "ansible.builtin.apt" not in install:
    fail("docker role must install pinned packages with apt")
if "item.version" not in str(install["ansible.builtin.apt"].get("name")):
    fail("docker role must consume docker_packages versions verbatim")

daemon = task_named(docker_tasks, "Configure conservative Docker daemon policy")
daemon_config = daemon.get("ansible.builtin.copy", {}).get("content", "")
for setting in ("live-restore", "log-driver", "max-size", "max-file"):
    if setting not in daemon_config:
        fail(f"daemon.json policy is missing {setting}")
if '"hosts"' in daemon_config or "tcp://" in daemon_config:
    fail("daemon.json must not configure a remote TCP API")
if "Restart Docker" not in str(daemon.get("notify")):
    fail("daemon.json changes must notify the Docker restart handler")

swarm_tasks = load("roles/swarm/tasks/main.yml")
inspect = task_named(swarm_tasks, "Inspect local Docker daemon")
if "community.docker.docker_host_info" not in inspect:
    fail("swarm role must inspect local Swarm state")

foreign = task_named(swarm_tasks, "Reject membership in a different Swarm")
if "ansible.builtin.assert" not in foreign or "swarm_existing_node.nodes" not in str(foreign):
    fail("swarm role must reject a node active in another Swarm")

init_identity = task_named(swarm_tasks, "Require init manager cluster identity")
init_identity_assert = str(init_identity.get("ansible.builtin.assert", {}))
if (
    "swarm_local_state" not in str(init_identity.get("when"))
    or "swarm_cluster_identity" not in init_identity_assert
    or "Swarm.Cluster.ID" not in init_identity_assert
):
    fail("active init manager must match its persisted Swarm cluster identity")

record_identity = task_named(swarm_tasks, "Record initialized Swarm cluster identity")
record_identity_copy = str(record_identity.get("ansible.builtin.copy", {}))
if "Swarm.Cluster.ID" not in record_identity_copy:
    fail("Swarm init must persist the initialized cluster identity")

record_addresses = task_named(swarm_tasks, "Record configured Swarm network addresses")
record_addresses_copy = record_addresses.get("ansible.builtin.copy", {})
record_addresses_text = str(record_addresses_copy)
for requirement in ("advertise_addr", "data_path_addr", "netbird_ip"):
    if requirement not in record_addresses_text:
        fail(f"Swarm must persist configured {requirement}")
if record_addresses_copy.get("mode") != "0600":
    fail("persisted Swarm network addresses must be root-only")
if "swarm_local_state == \"inactive\"" not in str(record_addresses.get("when")):
    fail("Swarm network addresses must only be persisted for a fresh init or join")

initialize = task_named(swarm_tasks, "Initialize Swarm on the init manager")
if initialize.get("community.docker.docker_swarm", {}).get("state") != "present":
    fail("init manager must initialize through community.docker.docker_swarm")
if "inactive" not in str(initialize.get("when")):
    fail("Swarm init must only run when the init manager is inactive")

tokens = task_named(swarm_tasks, "Fetch runtime Swarm join tokens")
if tokens.get("no_log") is not True or "delegate_to" not in tokens:
    fail("join tokens must be fetched at runtime from a manager under no_log")

join = task_named(swarm_tasks, "Join node to Swarm over Netbird")
join_args = join.get("community.docker.docker_swarm", {})
if join.get("no_log") is not True or join_args.get("state") != "join":
    fail("Swarm joins must use community.docker under no_log")
for key in ("advertise_addr", "data_path_addr", "remote_addrs", "join_token"):
    if key not in join_args:
        fail(f"Swarm join is missing {key}")

confirm = task_named(swarm_tasks, "Confirm joined node from a manager")
if "community.docker.docker_node_info" not in confirm or "delegate_to" not in confirm:
    fail("joined nodes must be confirmed from a manager")
confirmation = task_named(swarm_tasks, "Require expected Swarm node state")
confirmation_text = str(confirmation.get("ansible.builtin.assert", {}))
for requirement in ('"ready"', "Availability", "ManagerStatus"):
    if requirement not in confirmation_text:
        fail(f"manager confirmation must assert {requirement}")

for playbook_name in ("playbooks/greenfield.yml", "playbooks/join.yml"):
    plays = load(playbook_name)
    if any(play.get("serial") != 1 for play in plays):
        fail(f"{playbook_name} must keep every mutating play serial: 1")
    role_names = [
        role if isinstance(role, str) else role.get("role")
        for play in plays
        for role in play.get("roles", [])
    ]
    if "docker" not in role_names or "swarm" not in role_names:
        fail(f"{playbook_name} must wire both docker and swarm roles")

greenfield = load("playbooks/greenfield.yml")
init_plays = [
    play for play in greenfield if play.get("vars", {}).get("swarm_action") == "init"
]
if len(init_plays) != 1 or "groups['managers'][0]" not in str(init_plays[0].get("hosts")):
    fail("greenfield must initialize the first inventory manager in its own play")

print("OK: Docker and Swarm contracts are complete")
