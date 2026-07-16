# Netbird cloud agent enrollment on Ubuntu 24.04

Type: research
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What are the primary-source facts for installing and enrolling the Netbird **cloud** agent on Ubuntu 24.04 in an Ansible-driven bootstrap: install methods, setup-key (or equivalent) enrollment, interface/IP discovery after join, service management, and any constraints that affect a short public-SSH bootstrap window followed by Netbird-only SSH?

## Answer

On Ubuntu 24.04, install via NetBird’s APT repo (`pkgs.netbird.io/debian` → `apt install netbird`) or `curl -fsSL https://pkgs.netbird.io/install.sh | sh`; enroll unattended with `netbird up --setup-key <KEY>` (cloud default management `https://api.netbird.io:443`). After join, the overlay iface is `wt0`; discover the peer IP with `netbird status` / `netbird status -4` (or `ip addr show wt0`). Manage with systemd unit `netbird` (`systemctl enable/status`) or `netbird service *`. For the public-SSH → NetBird-only cutover: NetBird needs no inbound perimeter ports but does need outbound cloud control-plane/STUN/TURN; ensure Access Control allows TCP/22 (OpenSSH over mesh) or enable embedded NetBird SSH; if UFW is on, `ufw allow in on wt0`; verify mesh SSH before closing public :22. Avoid ephemeral setup keys for persistent hosts.

Findings: [docs/research/netbird-agent-enrollment.md](../../../docs/research/netbird-agent-enrollment.md)
