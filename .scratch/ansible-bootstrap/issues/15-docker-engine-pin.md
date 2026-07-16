# Docker Engine install channel

Type: grilling
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

Which Docker Engine install source/channel should Ansible use on Ubuntu 24.04, and should the design pin a version or float on a stable channel?

## Answer

- Install **Docker CE from Docker’s official apt repository** (not Ubuntu `docker.io`, not snap).
- **Pin** `docker-ce`, `docker-ce-cli`, `containerd.io` (and compose plugin if installed) via `group_vars` / inventory. Ansible converges hosts to those pins; upgrades = bump pins in git and re-run.
- Do **not** float to latest on every run; do **not** unattended-upgrade Docker packages.
- Implementation may use a maintained Galaxy/role that supports official CE + version pins; the design does not hard-require a specific role name.
