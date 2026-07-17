#!/usr/bin/env python3
"""Static contracts for the bootstrap-window lockdown roles."""

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


def task_module(task: dict) -> str | None:
    return next(
        (
            key
            for key in task
            if key.startswith("ansible.builtin.") or key.startswith("ansible.posix.")
        ),
        None,
    )


def task_named(tasks: list[dict], name: str) -> dict:
    return next((task for task in tasks if task.get("name") == name), {})


variables = load("group_vars/all.yml")
for variable in (
    "bootstrap_user_name",
    "bootstrap_ssh_public_keys_dir",
    "netbird_setup_key_file",
    "baseline_packages",
):
    if variable not in variables:
        fail(f"group_vars/all.yml is missing {variable}")

bootstrap_tasks = load("roles/bootstrap_user/tasks/main.yml")
create_user = task_named(bootstrap_tasks, "Create permanent automation user")
if task_module(create_user) != "ansible.builtin.user":
    fail("bootstrap_user must create the permanent automation user")
if not create_user["ansible.builtin.user"].get("password_lock"):
    fail("bootstrap_user must lock the automation user password")
if task_module(task_named(bootstrap_tasks, "Install operator SSH public keys")) != (
    "ansible.posix.authorized_key"
):
    fail("bootstrap_user must install public keys with authorized_key")
if task_module(task_named(bootstrap_tasks, "Prove automation user key login")) != (
    "ansible.builtin.wait_for_connection"
):
    fail("bootstrap_user must prove the switched SSH connection")

ssh_policy = load("roles/bootstrap_user/handlers/main.yml")
validate = task_named(ssh_policy, "Validate SSH configuration")
if validate.get("ansible.builtin.command", {}).get("cmd") != "/usr/sbin/sshd -t":
    fail("SSH handler must validate configuration before reload")

netbird_tasks = load("roles/netbird/tasks/main.yml")
status = task_named(netbird_tasks, "Check Netbird connection")
if status.get("ansible.builtin.command", {}).get("cmd") != "netbird status -C ready":
    fail("netbird must check readiness before enrollment")
enroll = task_named(netbird_tasks, "Enroll Netbird peer")
if enroll.get("no_log") is not True:
    fail("Netbird enrollment must use no_log")
if "netbird_status.rc != 0" not in str(enroll.get("when")):
    fail("Netbird enrollment must skip connected peers")
if task_module(task_named(netbird_tasks, "Switch Ansible to Netbird SSH")) != (
    "ansible.builtin.set_fact"
):
    fail("netbird must switch ansible_host after mesh SSH proof")

ufw_tasks = load("roles/ufw/tasks/main.yml")
ufw_rules = [
    task["community.general.ufw"]
    for task in ufw_tasks
    if "community.general.ufw" in task
]
if not any(rule.get("interface") == "wt0" and rule.get("direction") == "in" for rule in ufw_rules):
    fail("UFW must allow inbound traffic on wt0")
public_ports = {
    str(rule.get("port"))
    for rule in ufw_rules
    if rule.get("rule") == "allow" and rule.get("port") and not rule.get("delete")
}
if public_ports != {"80", "443"}:
    fail(f"UFW public ports must be exactly 80/443, got {sorted(public_ports)}")
if not any(
    rule.get("rule") == "allow"
    and rule.get("port") == "22"
    and rule.get("delete") is True
    for rule in ufw_rules
):
    fail("UFW must remove any existing public TCP/22 allow rule")

baseline_tasks = load("roles/baseline/tasks/main.yml")
if task_module(task_named(baseline_tasks, "Install practical baseline packages")) != (
    "ansible.builtin.apt"
):
    fail("baseline must install packages with apt")

for playbook in ("playbooks/greenfield.yml", "playbooks/join.yml"):
    plays = load(playbook)
    if not plays or plays[0].get("serial") != 1:
        fail(f"{playbook} must lock down new_nodes serially")
    lockdown_roles = [
        role if isinstance(role, str) else role.get("role")
        for role in plays[0].get("roles", [])
    ]
    if lockdown_roles != ["bootstrap_user", "netbird", "ufw", "baseline"]:
        fail(f"{playbook} must run all lockdown roles before later phases")

print("OK: Ansible lockdown contracts are complete")
