# Inventory and vars schema

Type: grilling
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What is the concrete inventory and variable schema for this environment template: host groups (`managers`, `workers`, `new_nodes` or equivalent), how public vs Netbird IPs are represented, SSH auth modes (key vs root password), where staged age key / git token / Netbird setup key live on the operator machine, and how join runs limit themselves to new hosts?

## Answer

One inventory per environment (this clone). Groups:

- `managers` / `workers` — Swarm role (every host in exactly one)
- `new_nodes` — lifecycle: hosts still in the bootstrap window; remove after Netbird lockdown

Host addressing:

- `public_ip`, `netbird_ip` (explicit vars)
- `ansible_host` = `public_ip` while in `new_nodes`; switch to `netbird_ip` after lockdown

SSH auth:

- Committed inventory holds non-secret shape (`ansible_user`, etc.)
- Password / private-key material and short-lived bootstrap SSH secrets live in **gitignored files at repo root** (usable only for the minutes-long bootstrap window)

Staged operator secrets (repo root, gitignored):

- `sops_age_key.txt`
- `git_access_token.txt`
- `netbird_setup_key.txt`
- Bootstrap SSH secret file(s) at root (same convention)

Join scoping:

- Bootstrap/join plays target `new_nodes`
- Join-token / control-plane contact uses existing managers already on Netbird (not in `new_nodes`)
- Operator adds host to `managers` or `workers` **and** `new_nodes` → run join → drop from `new_nodes` and set `ansible_host` to `netbird_ip`
