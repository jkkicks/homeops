#!/usr/bin/env python3
"""Static contracts for completion verification and repeat-safe entrypoints."""

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


def role_names(plays: list[dict]) -> list[str]:
    return [
        role if isinstance(role, str) else role.get("role")
        for play in plays
        for role in play.get("roles", [])
    ]


verify_tasks = load("roles/verify/tasks/main.yml")
requirement_names = {
    "HOST_BASELINE",
    "AUTOMATION_ACCESS",
    "NETBIRD_CONNECTIVITY",
    "UFW_PUBLIC_SURFACE",
    "DOCKER_RUNTIME",
    "FOREIGN_SWARM_MEMBERSHIP",
    "SWARM_DATA_PATH",
    "SWARM_NODE_STATE",
    "DOCO_CD_HEALTH",
    "JOIN_MANAGER_CONFIRMATION",
    "JOIN_DOCO_CD_NOT_REDEPLOYED",
}
task_text = yaml.safe_dump(verify_tasks)
for requirement_name in sorted(requirement_names):
    if f"REQUIREMENT {requirement_name}" not in task_text:
        fail(f"verify role must name REQUIREMENT {requirement_name}")
    requirement_task = next(
        (
            task
            for task in verify_tasks
            if task.get("name") == f"REQUIREMENT {requirement_name}"
        ),
        {},
    )
    assertion = requirement_task.get("ansible.builtin.assert", {})
    if f"REQUIREMENT {requirement_name} failed" not in assertion.get("fail_msg", ""):
        fail(f"REQUIREMENT {requirement_name} must have a specific failure message")

required_assertion_conditions = {
    "FOREIGN_SWARM_MEMBERSHIP": [
        "verify_docker_host.host_info.Swarm.Cluster.ID",
        "verify_manager_host.host_info.Swarm.Cluster.ID",
        "== verify_manager_host.host_info.Swarm.Cluster.ID",
    ],
    "SWARM_NODE_STATE": [
        'Spec.Role == verify_expected_swarm_role',
        'Spec.Availability == swarm_availability',
        'Status.Addr == netbird_ip',
    ],
    "SWARM_DATA_PATH": [
        "verify_swarm_network_addresses_file.stat.exists",
        "data_path_addr",
        "== netbird_ip",
        "12[0-7]",
    ],
}
for requirement_name, required_conditions in required_assertion_conditions.items():
    requirement_task = next(
        task
        for task in verify_tasks
        if task.get("name") == f"REQUIREMENT {requirement_name}"
    )
    conditions = yaml.safe_dump(
        requirement_task["ansible.builtin.assert"].get("that", [])
    )
    for required_condition in required_conditions:
        if required_condition not in conditions:
            fail(
                f"REQUIREMENT {requirement_name} must assert {required_condition}"
            )

if "Peers" in task_text or "verify_swarm_data_path_peers" in task_text:
    fail("verify role must not infer the local data-path address from VXLAN peers")

mutating_modules = {
    "ansible.builtin.apt",
    "ansible.builtin.copy",
    "ansible.builtin.file",
    "ansible.builtin.hostname",
    "ansible.builtin.package",
    "ansible.builtin.service",
    "ansible.builtin.systemd_service",
    "ansible.builtin.user",
    "community.docker.docker_node",
    "community.docker.docker_secret",
    "community.docker.docker_stack",
    "community.docker.docker_swarm",
    "community.general.ufw",
}
for task in verify_tasks:
    forbidden = mutating_modules.intersection(task)
    if forbidden:
        fail(f"verify role must not mutate state ({', '.join(sorted(forbidden))})")
    if "ansible.builtin.command" in task and task.get("changed_when") is not False:
        fail(f"verify command must set changed_when: false: {task.get('name')}")
    if "ansible.builtin.command" in task and task.get("check_mode") is not False:
        fail(f"verify command must execute in check mode: {task.get('name')}")

verify_playbook = load("playbooks/verify.yml")
if role_names(verify_playbook) != ["verify"]:
    fail("verify playbook must run only the verify role")
if any(play.get("check_mode") is not True for play in verify_playbook):
    fail("verify playbook must force check mode")

greenfield = load("playbooks/greenfield.yml")
if role_names(greenfield)[-1:] != ["verify"]:
    fail("greenfield must run the completion contract last")

join = load("playbooks/join.yml")
join_roles = role_names(join)
if join_roles[-1:] != ["verify"]:
    fail("join must run its completion contract last")
if "doco_cd" in join_roles:
    fail("join must never run the doco_cd role")
if "verify_doco_cd_version_before" not in yaml.safe_dump(join):
    fail("join must preserve doco-cd service version for no-redeploy verification")

makefile = (ROOT / "Makefile").read_text()
if "scripts/test-ansible-verify.py" not in makefile:
    fail("make lint must run the verify contract test")
if "$(PLAYBOOKS)/verify.yml" not in makefile:
    fail("make verify must invoke playbooks/verify.yml")

print("OK: completion and idempotency contracts are complete")
