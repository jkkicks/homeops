# Docker Swarm control plane over Netbird

Type: research
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What do Docker’s primary docs (and related first-party sources) say about initializing and joining Swarm with `--advertise-addr` / `--data-path-addr` (or equivalents) on a WireGuard-style overlay NIC such as Netbird: required flags, manager vs worker behavior, multi-homed host pitfalls, and what traffic stays on the Docker overlay vs the host mesh?

## Answer

Multi-homed hosts (Netbird `wt0` + other NICs) **must** set `--advertise-addr` to the mesh IP/interface on init and join; `--data-path-addr` is optional and defaults to advertise. That puts Swarm control and VXLAN underlay toward Netbird peers; container traffic stays on Docker overlay networks on top of that underlay. Open `2377/tcp`, `4789/udp`, and `7946/tcp+udp` between peers on the advertised path.

Findings: [docs/research/swarm-over-netbird.md](../../../docs/research/swarm-over-netbird.md)
