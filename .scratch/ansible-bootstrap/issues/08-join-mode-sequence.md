# Join-mode sequence

Type: grilling
Status: resolved
Blocked by: 02, 04, 06

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What is the ordered join-mode step list for adding managers or workers to an existing Swarm — including how join tokens are obtained from a current manager over Netbird, what is never touched (doco-cd, age/git secrets), and how Ansible chooses manager vs worker from inventory?

## Answer

### Never touched on join

- doco-cd (no redeploy, no reconfig)
- Age key / git token / Docker secrets for doco-cd

### A. Prep

1. Existing managers are already on Netbird (not in `new_nodes`; `ansible_host` = `netbird_ip`).
2. Add new host(s) to `managers` or `workers` **and** `new_nodes`; set `public_ip` + bootstrap SSH secrets; stage `netbird_setup_key.txt` as needed.
3. Manager vs worker is solely which inventory group the host is in.

### B. New host lockdown

4. Run [SSH and firewall lockdown sequence](06-ssh-firewall-lockdown-sequence.md) on each new host through Netbird + UFW + baseline.

### C. Swarm join

5. On an existing manager over Netbird: `docker swarm join-token manager` or `join-token worker` matching the new host’s group.
6. On the new node: `docker swarm join --token … --advertise-addr <netbird_ip|wt0> <manager-netbird-ip>:2377`.
7. Verify with `docker node ls` — new node Ready (Reachable if manager).
8. Host already left `new_nodes` with `ansible_host` = `netbird_ip` at mesh cutover (lockdown step).
