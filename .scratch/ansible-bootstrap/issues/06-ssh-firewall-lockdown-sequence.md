# SSH and firewall lockdown sequence

Type: grilling
Status: resolved
Blocked by: 01, 03

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

In what exact order should Ansible install repo SSH public keys, create the sudo user, enroll Netbird, switch `ansible_host` to the Netbird IP, close public SSH, and apply UFW — so the operator never loses the host and the bootstrap window stays minutes-short?

## Answer

**Netbird ASAP; UFW and package baseline after mesh cutover.** Normal OpenSSH over the mesh (not Netbird SSH).

Per host in `new_nodes`:

1. Connect over public SSH (provider key or root password).
2. Create sudo user → install repo SSH public keys → **prove a fresh key-based SSH login** as that user → point Ansible at that user.
3. Disable password authentication and root SSH (still on public IP, key-only).
4. Install/enroll Netbird; record `netbird_ip` (`wt0` / `netbird status -4`).
5. From the operator on Netbird, **prove OpenSSH to `netbird_ip`** → set `ansible_host` to `netbird_ip`, remove host from `new_nodes`.
6. Enable UFW: `allow in on wt0`, allow `80`/`443`, then `ufw enable` — **do not** allow public OpenSSH (closes public :22).
7. Remaining baseline packages / hardening over Netbird only.

Rationale: shortest path to mesh; password/root dropped only after proven key login on public; public SSH dropped only after proven mesh SSH + UFW without a public :22 allow.
