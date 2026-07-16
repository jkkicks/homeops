# Greenfield sequence and doco-cd verification

Type: grilling
Status: resolved
Blocked by: 01, 02, 03, 05

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What is the ordered greenfield step list from staged secrets (`make` age key, git token, backup confirmation) through Swarm init/join, secret creation, doco-cd deploy, local credential scrub, and the precise checks that mean “doco-cd is verified and polling”?

## Answer

### A. Operator prep (before hosts)

1. Inventory ready: `managers` / `workers`, all hosts in `new_nodes`, `public_ip`, SSH shape; staged bootstrap SSH secrets at repo root.
2. `make` generates `sops_age_key.txt` and updates committed `age.pubkey` / `.sops.yaml` (commit + push).
3. Stage `git_access_token.txt` and `netbird_setup_key.txt` at repo root.
4. Ansible requires explicit confirmation that the age private key is backed up offline.

### B. Per-host lockdown

5. Run the sequence from [SSH and firewall lockdown sequence](06-ssh-firewall-lockdown-sequence.md) on all `new_nodes` (Netbird ASAP → UFW → baseline over mesh).

### C. Swarm (over Netbird)

6. Install Docker Engine on all nodes.
7. First manager: `docker swarm init --advertise-addr <netbird_ip|wt0>`.
8. Remaining managers/workers join with `--advertise-addr` on Netbird.
9. Operator may use a Docker context to a manager over Netbird SSH.

### D. doco-cd

10. Create external Docker secrets `sops_age_key` and `git_access_token` from staged files (same labeling intent as today’s bootstrap).
11. Poll config points at this clone’s HTTPS remote (committed; path today `bootstrap/doco-cd`, design target `apps/doco-cd`).
12. `docker stack deploy` the doco-cd stack.
13. **Verified when:** `doco-cd` service is `1/1`; logs show poll config loaded and a successful repo clone/poll within `interval`; no repeated auth or decrypt errors. (Deploying other `apps/` stacks is the apps workflow after real secrets exist — not the greenfield gate.)
14. Scrub local staged secrets (`sops_age_key.txt`, `git_access_token.txt`, bootstrap SSH secrets, etc.) after backup confirmation already satisfied.
