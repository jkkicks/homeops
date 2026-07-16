# Ubuntu 24.04 practical hardening baseline

Type: research
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What does Ubuntu’s (and adjacent first-party) guidance recommend for a **practical** 24.04 server baseline suitable for a minutes-long public SSH bootstrap window: UFW, SSH hardening, unattended-upgrades, NTP, user/sudo setup, and safe ordering when password/root SSH may be required at first login then removed — explicitly **excluding** fail2ban?

## Answer

Practical 24.04 baseline: enable UFW only after allowing OpenSSH; keep `unattended-upgrades` and `systemd-timesyncd`; use a sudo user with SSH keys; leave password/root SSH only until key login is proven, then disable via a winning `sshd_config.d` drop-in (watch cloud-init’s `50-cloud-init.conf` / `KbdInteractiveAuthentication`). No fail2ban.

Findings: [docs/research/ubuntu-hardening-baseline.md](../../../docs/research/ubuntu-hardening-baseline.md)
