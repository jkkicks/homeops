# Netbird SSH ACL policy

Type: grilling
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What Netbird group/ACL policy should the design prescribe so operators (and Ansible) can SSH to Swarm nodes over the mesh after public :22 is closed — without over-specifying the whole Netbird tenancy?

## Answer

**Ansible never manages Netbird** (groups, ACLs, setup keys beyond reading `netbird_setup_key.txt` for `netbird up`).

**Per-environment group** (name documented / `group_vars`, e.g. `{env}-operators`):

- Setup keys auto-assign **Swarm nodes** into this group.
- **Operator peers** (including the operator machine) are added to the same group.
- **Full access within the group** — covers OpenSSH :22 and Swarm control/data over the mesh.

**Additional ACL:** any Netbird peer → nodes in that group, **TCP 80/443** (private Traefik / mesh HTTP(S)). Public internet 80/443 remains host UFW on the public NIC.

Dashboard/runbook only; design documents the pattern.
