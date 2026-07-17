#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

need_file() {
  [[ -f "$1" ]] || fail "missing required file: $1"
}

need_text() {
  grep -Fq -- "$2" "$1" || fail "$1 is missing: $2"
}

for path in \
  Makefile \
  bootstrap/ansible/ansible.cfg \
  bootstrap/ansible/requirements.yml \
  bootstrap/ansible/inventory/hosts.yml \
  bootstrap/ansible/inventory/group_vars/all.yml \
  bootstrap/ansible/secrets/README.md \
  bootstrap/ansible/playbooks/greenfield.yml \
  bootstrap/ansible/playbooks/join.yml \
  bootstrap/ansible/playbooks/verify.yml \
  bootstrap/ansible/README.md \
  sops_age_key.txt.example \
  git_access_token.txt.example \
  netbird_setup_key.txt.example \
  bootstrap_ssh_private_key.example \
  bootstrap_ssh_password.txt.example \
  ssh-keys/README.md
do
  need_file "$path"
done

for role in bootstrap_user netbird ufw baseline docker swarm doco_cd verify; do
  need_file "bootstrap/ansible/roles/$role/tasks/main.yml"
done

for target in age-key greenfield join verify lint; do
  grep -Eq "^${target}:" Makefile || fail "Makefile is missing target: $target"
done

need_text bootstrap/ansible/inventory/group_vars/all.yml 'timezone: UTC'
need_text bootstrap/ansible/inventory/group_vars/all.yml '5:29.6.1-1~ubuntu.24.04~noble'
need_text bootstrap/ansible/inventory/group_vars/all.yml '2.2.5-1~ubuntu.24.04~noble'
need_text bootstrap/ansible/inventory/group_vars/all.yml '0.35.0-1~ubuntu.24.04~noble'
need_text bootstrap/ansible/inventory/group_vars/all.yml '5.3.1-1~ubuntu.24.04~noble'

for group in managers workers new_nodes; do
  need_text bootstrap/ansible/inventory/hosts.yml "${group}:"
done

need_text bootstrap/ansible/requirements.yml 'community.docker'
grep -Eq 'version: "[0-9]+\.[0-9]+\.[0-9]+"' bootstrap/ansible/requirements.yml ||
  fail "requirements.yml must use exact dependency versions"

for secret in \
  sops_age_key.txt \
  git_access_token.txt \
  netbird_setup_key.txt \
  bootstrap_ssh_private_key \
  bootstrap_ssh_password.txt
do
  git check-ignore -q "$secret" || fail "$secret must be ignored"
done

if git check-ignore -q bootstrap/ansible/secrets/example.sops.yml; then
  fail "SOPS ciphertext under bootstrap/ansible/secrets must be trackable"
fi

ok "Ansible bootstrap skeleton is complete"
