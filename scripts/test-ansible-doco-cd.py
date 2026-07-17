#!/usr/bin/env python3
"""Static contracts for doco-cd bootstrap and operator secret cleanup."""

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE = ROOT / "bootstrap" / "ansible"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text())


def task_named(tasks: list[dict], name: str) -> dict:
    return next((task for task in (tasks or []) if task.get("name") == name), {})


for relative_path in ("compose.yaml", "poll-config.yaml", "secrets/README.md"):
    if not (ROOT / "apps" / "doco-cd" / relative_path).is_file():
        fail(f"apps/doco-cd/{relative_path} must be the canonical doco-cd source")
if (ROOT / "bootstrap" / "doco-cd" / "compose.yaml").exists():
    fail("bootstrap/doco-cd/compose.yaml must be removed after migration")
doco_cd_configs = list(yaml.safe_load_all((ROOT / ".doco-cd.yaml").read_text()))
if any(config.get("working_dir") == "bootstrap/doco-cd" for config in doco_cd_configs):
    fail("doco-cd configuration must not reference the removed bootstrap path")
app_discovery = [
    config
    for config in doco_cd_configs
    if config.get("working_dir") == "apps"
    and config.get("auto_discovery", {}).get("enabled") is True
]
if len(app_discovery) != 1:
    fail("apps auto-discovery must include the migrated doco-cd application")
if any(config.get("working_dir") == "apps/doco-cd" for config in doco_cd_configs):
    fail("doco-cd must not be configured twice beside apps auto-discovery")

role_tasks = load(ANSIBLE / "roles" / "doco_cd" / "tasks" / "main.yml")
inspect_secrets = task_named(role_tasks, "Inspect bootstrap Docker secrets")
inspect_argv = inspect_secrets.get("ansible.builtin.command", {}).get("argv", [])
inspect_command = " ".join(str(argument) for argument in inspect_argv)
if "docker secret inspect" not in inspect_command or inspect_secrets.get("changed_when") is not False:
    fail("doco_cd must inspect existing Docker secrets before creating them")

decrypt = task_named(role_tasks, "Decrypt retained Git access token")
decrypt_argv = decrypt.get("ansible.builtin.command", {}).get("argv", [])
if not all(argument in decrypt_argv for argument in ("--output-type", "binary")):
    fail("retained Git token must decrypt to its original raw value")

for task_name, secret_name in (
    ("Create missing age Docker secret", "sops_age_key"),
    ("Create missing Git access token Docker secret", "git_access_token"),
):
    task = task_named(role_tasks, task_name)
    secret = task.get("community.docker.docker_secret", {})
    if task.get("no_log") is not True or secret.get("name") != secret_name:
        fail(f"{task_name} must create {secret_name} under no_log")
    if ".rc != 0" not in str(task.get("when")):
        fail(f"{task_name} must leave an existing Docker secret untouched")

stack_ls = task_named(role_tasks, "List Swarm stacks")
if "stack" not in str(stack_ls.get("ansible.builtin.command", {})):
    fail("doco_cd must list stacks with docker stack ls before deploy decisions")

stage = task_named(role_tasks, "Stage canonical doco-cd application files")
stage_text = str(stage.get("ansible.builtin.copy", {}))
if "apps/doco-cd" not in stage_text:
    fail("doco_cd must stage apps/doco-cd only while restoring an absent stack")
if "doco-cd' not in doco_cd_stack_ls.stdout_lines" not in str(stage.get("when")):
    fail("doco_cd staging must skip when the doco-cd stack already exists")

deploy = task_named(role_tasks, "Deploy missing doco-cd stack")
deploy_args = deploy.get("community.docker.docker_stack", {})
if (
    deploy_args.get("name") != "doco-cd"
    or "compose.yaml" not in str(deploy_args.get("compose"))
    or "doco-cd' not in doco_cd_stack_ls.stdout_lines" not in str(deploy.get("when"))
):
    fail("doco_cd must deploy the canonical compose only when the stack is absent")

greenfield = load(ANSIBLE / "playbooks" / "greenfield.yml")
greenfield_roles = [
    role if isinstance(role, str) else role.get("role")
    for play in greenfield
    for role in play.get("roles", [])
]
if "doco_cd" not in greenfield_roles:
    fail("greenfield must include the doco_cd role")

join = load(ANSIBLE / "playbooks" / "join.yml")
join_roles = [
    role if isinstance(role, str) else role.get("role")
    for play in join
    for role in play.get("roles", [])
]
if "doco_cd" in join_roles:
    fail("join must not include the doco_cd role")

cleanup_tasks = load(ANSIBLE / "tasks" / "encrypt-and-cleanup.yml")
encrypt = task_named(cleanup_tasks, "Encrypt Git access token with SOPS")
encrypt_argv = encrypt.get("ansible.builtin.command", {}).get("argv", [])
encrypt_command = " ".join(str(argument) for argument in encrypt_argv)
if (
    "doco_cd_git_token_file" not in encrypt_command
    or "doco_cd_git_token_sops_file" not in encrypt_command
    or encrypt.get("no_log") is not True
):
    fail("cleanup must SOPS-encrypt the Git token into bootstrap/ansible/secrets")

ciphertext_path = "bootstrap/ansible/secrets/git_access_token.sops.yml"
stage_ciphertext = task_named(cleanup_tasks, "Stage Git access token ciphertext")
check_commit = task_named(cleanup_tasks, "Check staged Git access token ciphertext")
commit_ciphertext = task_named(cleanup_tasks, "Commit Git access token ciphertext")
verify_commit = task_named(cleanup_tasks, "Verify Git access token ciphertext is committed")
require_commit = task_named(cleanup_tasks, "Require committed Git access token ciphertext")
check_argv = check_commit.get("ansible.builtin.command", {}).get("argv", [])
commit_argv = commit_ciphertext.get("ansible.builtin.command", {}).get("argv", [])
verify_argv = verify_commit.get("ansible.builtin.command", {}).get("argv", [])
if stage_ciphertext.get("when") is not None or check_commit.get("when") is not None:
    fail("ciphertext staging and commit checks must run even when root plaintext is absent")
if stage_ciphertext.get("changed_when") is not False:
    fail("ciphertext staging must be idempotent when the committed file is unchanged")
if not all(argument in check_argv for argument in ("diff", "--cached", "--quiet", ciphertext_path)):
    fail("cleanup must check whether the intended ciphertext path needs committing")
if (
    check_commit.get("changed_when") is not False
    or "rc not in [0, 1]" not in str(check_commit.get("failed_when"))
):
    fail("ciphertext commit check must treat clean and changed states idempotently")
if not all(argument in commit_argv for argument in ("commit", "--only", ciphertext_path)):
    fail("cleanup must commit only the intended Git token ciphertext path")
if "-m" not in commit_argv or "rc == 1" not in str(commit_ciphertext.get("when")):
    fail("cleanup must commit changed ciphertext and skip already-clean runs")
if "staged_git_access_token.stat.exists" in str(commit_ciphertext.get("when")):
    fail("ciphertext commit must not depend on root plaintext still existing")
if not all(argument in verify_argv for argument in ("diff", "--quiet", "HEAD", ciphertext_path)):
    fail("cleanup must verify ciphertext matches HEAD before deleting plaintext")
if require_commit.get("ansible.builtin.assert", {}).get("that") != [
    "committed_git_access_token.rc == 0"
]:
    fail("cleanup must refuse plaintext deletion unless ciphertext is committed")

task_names = [task.get("name") for task in cleanup_tasks]
if not (
    task_names.index(stage_ciphertext.get("name"))
    < task_names.index(check_commit.get("name"))
    < task_names.index(commit_ciphertext.get("name"))
    < task_names.index(verify_commit.get("name"))
    < task_names.index(require_commit.get("name"))
    < task_names.index("Delete bootstrap-window plaintext")
):
    fail("ciphertext must be staged and committed before plaintext deletion")

variables = load(ANSIBLE / "inventory" / "group_vars" / "all.yml")
if "git_access_token.txt" not in variables.get("doco_cd_git_token_file", ""):
    fail("Git token plaintext source must be the gitignored root file")
if "secrets/git_access_token.sops.yml" not in variables.get(
    "doco_cd_git_token_sops_file", ""
):
    fail("Git token ciphertext must live under bootstrap/ansible/secrets")

cleanup = task_named(cleanup_tasks, "Delete bootstrap-window plaintext")
deleted_paths = str(cleanup.get("ansible.builtin.file", {})) + str(cleanup.get("loop", []))
for filename in (
    "git_access_token.txt",
    "netbird_setup_key.txt",
    "sops_age_key.txt",
    "bootstrap_ssh_private_key",
    "bootstrap_ssh_password.txt",
):
    if filename not in deleted_paths:
        fail(f"cleanup must delete {filename}")
if any("age" in path.name and path.name != "README.md" for path in (ANSIBLE / "secrets").iterdir()):
    fail("the age private key must never be written under bootstrap/ansible/secrets")

makefile = (ROOT / "Makefile").read_text()
if "AGE_BACKUP_CONFIRMED" not in makefile or "test-ansible-doco-cd.py" not in makefile:
    fail("Makefile must require age backup confirmation and run this contract")

print("OK: doco-cd and SOPS cleanup contracts are complete")
