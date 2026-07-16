# Playbook, role, and make shape

Type: grilling
Status: resolved
Blocked by: 04, 07, 08

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What Ansible layout (roles vs playbooks vs tags) and operator `make` (or equivalent) targets should the design prescribe so greenfield and join are obvious, idempotent where safe, and aligned with the agreed secrets workflow — still as design, not implementation?

## Answer

### Make (repo root)

- `make age-key` — generate `sops_age_key.txt`; refresh committed `age.pubkey` / `.sops.yaml`
- `make greenfield` — age-backup confirmation gate → greenfield playbook
- `make join` — join playbook (`new_nodes` only)
- Optional later: `make check` (doco-cd verify-only) — not required for v1

### Ansible layout (prescribed, not implemented in this map)

```
ansible/
  inventory/hosts.yml
  group_vars/all.yml
  playbooks/
    greenfield.yml    # gates + lockdown + swarm + doco-cd
    join.yml          # lockdown + join only
  roles/
    bootstrap_user    # sudo user, repo SSH keys, sshd harden
    netbird
    ufw
    baseline          # packages after mesh
    docker
    swarm             # init vs join by inventory group
    doco_cd           # secrets + stack deploy + verify (greenfield only)
ssh-keys/             # committed public keys only
```

Two playbook entrypoints; roles composed in the locked sequences. No tag-driven matrix for v1.
