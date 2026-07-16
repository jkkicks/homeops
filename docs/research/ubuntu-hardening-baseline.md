# Ubuntu 24.04 practical hardening baseline

Research for a minutes-long public SSH bootstrap window: UFW, SSH hardening, unattended-upgrades, NTP, user/sudo, and safe ordering when password/root SSH may be required at first login then removed.

**Scope:** practical baseline (not CIS/USG score chase). **Explicitly excludes fail2ban.**

Primary sources: Ubuntu Server docs, Ubuntu Security docs, OpenSSH `sshd_config(5)`, cloud-init (Canonical), Ubuntu 24.04 release notes (fetched 2026-07-15).

---

## 1. Framing: practical vs compliance

Ubuntu Server’s security intro states a fresh install is usually safe for immediate use, and recommends a **layered** approach rather than a single control. ([Introduction to security](https://documentation.ubuntu.com/server/explanation/intro-to/security/))

The Server security how-to lists a practical starter set: **user management**, **firewalls**, AppArmor, console security — not CIS by default. ([Security how-to](https://documentation.ubuntu.com/server/how-to/security/))

Ubuntu Security’s “unnecessarily open ports” guidance: keep listening services minimal, **use a firewall** to limit who can reach open ports, and **keep software updated**. ([Unnecessarily open ports](https://documentation.ubuntu.com/security/common-mistakes/unnecessarily-open-ports/))

CIS/USG is available for compliance automation but is out of scope for a practical bootstrap baseline. ([USG / CIS](https://documentation.ubuntu.com/security/compliance/usg/))

---

## 2. UFW (host firewall)

### 2.1 Defaults and role

- `ufw` is Ubuntu’s default host-firewall frontend; it is **disabled by default**. ([Firewalls — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/firewalls/); [Firewall — Ubuntu Security](https://documentation.ubuntu.com/security/security-features/network/firewall/))
- Ubuntu Security documents `ufw` for 24.04 LTS (package `ufw` 0.36.2-6) and points configuration details at the Server docs. ([same](https://documentation.ubuntu.com/security/security-features/network/firewall/))
- Default policy when enabled (community wiki / typical `ufw status verbose`): **deny incoming**, **allow outgoing**. ([UFW Community Help Wiki](https://help.ubuntu.com/community/UFW))

### 2.2 SSH-safe enable order

Canonical first-party guidance (Kubernetes UFW how-to) states the critical order explicitly:

1. `sudo ufw allow OpenSSH` (or equivalent allow for SSH)
2. **then** `sudo ufw enable`

so SSH is not cut off when the default deny-incoming policy activates. ([Canonical Kubernetes — UFW](https://documentation.ubuntu.com/canonical-kubernetes/latest/snap/howto/networking/ufw/))

Ubuntu Server docs show the same primitives: `sudo ufw allow 22` / service name `ssh`, then `sudo ufw enable`; also `ufw allow` from a specific host/subnet to port 22 for tighter sources. ([Firewalls](https://documentation.ubuntu.com/server/how-to/security/firewalls/))

Application profiles live under `/etc/ufw/applications.d`; `sudo ufw app list` / `ufw allow <App>` (e.g. OpenSSH) is the profile-based form. ([same](https://documentation.ubuntu.com/server/how-to/security/firewalls/))

### 2.3 Rate limiting without fail2ban

Server docs’ `--dry-run` example exposes UFW’s built-in `ufw-user-limit` chain (log at 3/minute then REJECT). Full `limit` rule syntax is documented in `ufw(8)`, which the Server firewall page tells operators to read (`man ufw`). ([Firewalls](https://documentation.ubuntu.com/server/how-to/security/firewalls/))

For a short public SSH window, prefer **`ufw allow OpenSSH`** (or `ufw limit` once validated against `ufw(8)`) over installing fail2ban — out of ticket scope and unnecessary for a minutes-long window.

### 2.4 Logging and later narrowing

- Optional: `sudo ufw logging on`. ([Firewalls](https://documentation.ubuntu.com/server/how-to/security/firewalls/))
- Later lockdown (e.g. SSH only from NetBird overlay / specific CIDRs) uses the same host/subnet allow syntax; that sequencing belongs with the SSH/firewall lockdown ticket, not this baseline.

### 2.5 Caveat (provider images)

Ubuntu 24.04 release notes: Oracle Cloud images **no longer ship ufw** by default (conflicts with Oracle’s iptables-persistent path). Not the general Ubuntu Server case, but relevant if a provider image differs. ([24.04 release notes](https://documentation.ubuntu.com/release-notes/24.04/))

---

## 3. SSH hardening (OpenSSH)

### 3.1 Config model on Ubuntu

- Configure via `/etc/ssh/sshd_config` **or** drop-ins in `/etc/ssh/sshd_config.d/`.
- Ubuntu’s main file includes `Include /etc/ssh/sshd_config.d/*.conf` **at the top**. OpenSSH uses the **first** value for most directives, so drop-ins override the main file. ([OpenSSH server — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/); [sshd_config(5)](https://man.openbsd.org/sshd_config.5))
- Prefer snippets in `sshd_config.d/` for custom policy. ([OpenSSH server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/))

### 3.2 Safe change procedure (remote)

Ubuntu Server warns: if SSH is the only access path, a bad `sshd` config can lock you out; an incorrect directive may prevent start. Recommended steps:

1. `sudo sshd -t` after edits
2. Restart/reload only after the test passes: `sudo systemctl restart ssh.service` (Ubuntu docs); Ubuntu Security’s banner example uses `systemctl reload ssh.service`
3. Keep a backup of the original config before editing

([OpenSSH server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/); [OpenSSH Server banner](https://documentation.ubuntu.com/security/security-features/network/version-banners/openssh-server/))

### 3.3 Keys over passwords (end state)

- Ubuntu recommends **ed25519** keys (`ssh-keygen -t ed25519`), install pubkey into `~/.ssh/authorized_keys` (e.g. `ssh-copy-id`), and fix permissions (`chmod go-w .ssh/authorized_keys`). ([OpenSSH server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/))
- OpenSSH defaults (upstream): `PubkeyAuthentication yes`, `PasswordAuthentication yes`, `PermitRootLogin prohibit-password`. ([sshd_config(5)](https://man.openbsd.org/sshd_config.5))

### 3.4 cloud-init / installer password-auth footgun (24.04)

On many Ubuntu 24.04 installs (Subiquity / cloud-init), `PasswordAuthentication` may be forced via:

`/etc/ssh/sshd_config.d/50-cloud-init.conf`

Because that file is included **before** settings in the main `sshd_config`, editing only `/etc/ssh/sshd_config` often **does nothing**. ([Launchpad #2088207](https://bugs.launchpad.net/cloud-init/+bug/2088207); Ubuntu Server first-wins note above)

cloud-init’s `ssh_pwauth` key controls whether sshd accepts password auth (`true`/`false`; default leave unchanged). Disabling is limited to writing `PasswordAuthentication no`; on PAM-heavy images, also set `KbdInteractiveAuthentication no` (example drop-in `70-no-pam-password-auth.conf`). ([cloud-init — Set Passwords](https://cloudinit.readthedocs.io/en/latest/reference/modules.html#set-passwords))

**Practical disable pattern after keys work:**

- Write an early drop-in (lexically before `50-cloud-init.conf`), e.g. `01-hardening.conf`, **or** remove/override `50-cloud-init.conf`
- Set at least: `PasswordAuthentication no`, and usually `KbdInteractiveAuthentication no`
- Optionally `PermitRootLogin no` (stricter than OpenSSH’s `prohibit-password`)
- Validate effective config: `sudo sshd -T | grep -i passwordauthentication` (and related knobs)
- Apply with reload/restart only after `sshd -t` and a verified second key-based session

### 3.5 Restrict who may SSH

Ubuntu user-management docs: create a group (e.g. `sshlogin`), set `AllowGroups sshlogin` in sshd config, add permitted users, restart SSH. ([User management](https://documentation.ubuntu.com/server/how-to/security/user-management/))

Note: locking a user’s password does **not** block SSH if `authorized_keys` remains; remove/rename `~/.ssh/` to cut key access. ([same](https://documentation.ubuntu.com/server/how-to/security/user-management/))

### 3.6 Optional: banner / OS string

`DebianBanner no` in a drop-in suppresses the Ubuntu OS string in the pre-auth banner; reload `ssh.service`. ([OpenSSH Server — Ubuntu Security](https://documentation.ubuntu.com/security/security-features/network/version-banners/openssh-server/))

### 3.7 24.04 socket activation note

Since 22.10, `openssh-server` uses systemd socket activation; 24.04 reads `sshd_config` / `sshd_config.d` via a generator for `ssh.socket`. Operators should treat `ssh.service` / socket units as the Ubuntu-managed units (not assume classic always-on `sshd` alone). ([24.04 release notes — OpenSSH](https://documentation.ubuntu.com/release-notes/24.04/))

---

## 4. unattended-upgrades

- From 18.04 onward, `unattended-upgrades` is in default Desktop **and Server** installs and applies **security updates daily**. ([Security updates](https://documentation.ubuntu.com/security/security-updates/))
- Defaults described there: security updates after ~24 hours; normal updates after ~7 days (APT periodic settings).
- On Server: prefer a **drop-in** under `/etc/apt/apt.conf.d/` (name after `50unattended-upgrades`, e.g. `60…`) — do **not** edit the packaged `50unattended-upgrades`. Or run `sudo dpkg-reconfigure unattended-upgrades`. ([same](https://documentation.ubuntu.com/security/security-updates/))
- Logs: `/var/log/unattended-upgrades/unattended-upgrades.log`. ([same](https://documentation.ubuntu.com/security/security-updates/))
- Ubuntu 24.04: `needrestart` systematically restarts services affected by library upgrades during unattended upgrades (security-updates-only default makes skipping restarts unsafe). Exclude specific units via `needrestart` `override_rc` if required. ([24.04 release notes](https://documentation.ubuntu.com/release-notes/24.04/))

**Bootstrap implication:** ensure the package is present/enabled; do not chase Pro/ESM in the minimal baseline unless desired later. Ubuntu’s intro recommends ESM/Livepatch via Ubuntu Pro as optional hardening layers. ([Introduction to security](https://documentation.ubuntu.com/server/explanation/intro-to/security/))

---

## 5. NTP / time sync (24.04)

- Ubuntu Server’s time-sync explanation: **`chrony` becomes the default in 25.10**; on 25.04 and below (including **24.04**), **`systemd-timesyncd`** is typically the active client. Upgrades may leave timesyncd active and chrony disabled. ([About time synchronization](https://documentation.ubuntu.com/server/explanation/networking/about-time-synchronisation/))
- For 24.04 practical baseline: keep **`systemd-timesyncd`**, verify with `timedatectl status` (`System clock synchronized: yes`, `NTP service: active`) and `systemctl status systemd-timesyncd`. Servers/FallbackNTP in `/etc/systemd/timesyncd.conf` (+ `.d/`). ([timedatectl and timesyncd](https://documentation.ubuntu.com/server/how-to/networking/timedatectl-and-timesyncd/))
- If `chrony` is installed, `timedatectl` defers to it so two daemons do not conflict — do not run both as clients. ([same](https://documentation.ubuntu.com/server/how-to/networking/timedatectl-and-timesyncd/); [About time synchronization](https://documentation.ubuntu.com/server/explanation/networking/about-time-synchronisation/))
- Installing chrony to **serve** NTP is optional and not required for a host baseline. ([Serve NTP with chrony](https://documentation.ubuntu.com/server/how-to/networking/serve-ntp-with-chrony/))

Correct wall-clock time matters for TLS, logs, and unattended-upgrades scheduling; verifying sync once during bootstrap is enough for a practical baseline.

---

## 6. User and sudo setup

### 6.1 Root and sudo (Ubuntu default model)

- Administrative **root login is disabled by default** (password hash matches no value); day-to-day admin uses **`sudo`**. ([User management](https://documentation.ubuntu.com/server/how-to/security/user-management/))
- Installer-created initial user is in the **`sudo` group** (authorized via `/etc/sudoers`). Grant others full sudo by adding them to `sudo`. ([same](https://documentation.ubuntu.com/server/how-to/security/user-management/))
- Enable root password only if needed: `sudo passwd` (sets root). Disable again: `sudo passwd -l root`. ([same](https://documentation.ubuntu.com/server/how-to/security/user-management/))

### 6.2 Creating operators

- Prefer `adduser` / `addgroup` (Debian/Ubuntu). ([same](https://documentation.ubuntu.com/server/how-to/security/user-management/))
- From Ubuntu 21.10+, new home dirs default to **`0750`**. ([same](https://documentation.ubuntu.com/server/how-to/security/user-management/))
- Password policy knobs (`pam_unix` `minlen`, `chage`) exist for password-based access; for key-only SSH end state they matter less. ([same](https://documentation.ubuntu.com/server/how-to/security/user-management/))

### 6.3 Bootstrap implication

For provider VMs that hand out a password or enable root SSH temporarily: create/ensure a normal sudo user with **deployed authorized_keys**, keep using that account for Ansible, then remove password/root SSH (section 7) rather than operating as root long-term.

---

## 7. Safe ordering (password/root SSH → keys-only)

Derived from Ubuntu/OpenSSH/cloud-init rules above. Suitable for a **minutes-long** public SSH window.

| Step | Action | Why |
| --- | --- | --- |
| 1 | Reach host with whatever the provider gave (password and/or root). | Initial access only. |
| 2 | Ensure a non-root sudo user exists; install operator **public keys** in that user’s `authorized_keys`; verify `chmod` on keys. | Ubuntu key guidance; sudo model. |
| 3 | Open a **second** SSH session with **pubkey** as that sudo user; keep the first session until verified. | Avoid lockout (Ubuntu remote-sshd warning). |
| 4 | `ufw allow OpenSSH` (or `allow 22` / `allow ssh`), then `ufw enable`; `ufw status`. | Canonical allow-before-enable order. |
| 5 | Confirm `unattended-upgrades` enabled; `timedatectl status` shows sync. | Default Ubuntu update + 24.04 timesyncd path. |
| 6 | Only after key login works: disable password SSH via **winning** `sshd_config.d` drop-in (or clear `50-cloud-init.conf`); set `KbdInteractiveAuthentication no` if needed; optionally `PermitRootLogin no`; `sshd -t` then reload/restart; confirm with `sshd -T`. | First-wins + cloud-init behavior. |
| 7 | If a root password was set for bootstrap: `passwd -l root`. | Ubuntu root-disable guidance. |
| 8 | Do **not** drop public SSH / tighten UFW sources until mesh/VPN path is verified (separate lockdown ticket). | Operational; pairs with NetBird research. |

**Do not** disable password auth or enable UFW before confirming an alternate working login path.

---

## 8. Recommended practical baseline (summary)

| Area | 24.04 practical setting |
| --- | --- |
| UFW | Install if missing; `allow OpenSSH` then `enable`; default deny-in/allow-out; optional logging; optional source narrowing later |
| SSH end state | Key-only for sudo users; `PasswordAuthentication no` (+ `KbdInteractiveAuthentication no` as needed); prefer `PermitRootLogin no` or leave `prohibit-password`; drop-ins in `sshd_config.d/`; `sshd -t` before apply |
| SSH during window | Password/root may remain until step 6 |
| Updates | Keep `unattended-upgrades` (default); drop-ins only; expect `needrestart` service restarts on 24.04 |
| NTP | `systemd-timesyncd` + `timedatectl`; do not dual-run chrony unless intentionally switching |
| Users | No direct root habit; sudo group; keys in operator `authorized_keys` |
| Out of scope | fail2ban, CIS/USG full profiles, AppArmor policy authoring, Livepatch/Pro (optional later) |

---

## 9. Fact summary for implementers

| Topic | Primary fact |
| --- | --- |
| Fresh install | Layered baseline (users, firewall, updates); not CIS-first |
| UFW | Disabled by default; allow SSH **before** `ufw enable` |
| SSH config | First-wins; use `sshd_config.d/`; watch `50-cloud-init.conf` |
| Password off | After key proof; `ssh_pwauth` / drop-in; often need `KbdInteractiveAuthentication no` |
| Root | Ubuntu disables root password login by default; `PermitRootLogin` OpenSSH default `prohibit-password` |
| Updates | `unattended-upgrades` default on Server; 24.04 needrestart restarts services |
| Time | 24.04: timesyncd; chrony default only from 25.10 |
| fail2ban | Excluded; use short window + UFW + key cutover |

---

## Sources

- [Introduction to security — Ubuntu Server](https://documentation.ubuntu.com/server/explanation/intro-to/security/)
- [Security how-to — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/)
- [User management — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/user-management/)
- [Firewalls — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/firewalls/)
- [OpenSSH server — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/)
- [timedatectl and timesyncd — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/networking/timedatectl-and-timesyncd/)
- [About time synchronization — Ubuntu Server](https://documentation.ubuntu.com/server/explanation/networking/about-time-synchronisation/)
- [Serve NTP with chrony — Ubuntu Server](https://documentation.ubuntu.com/server/how-to/networking/serve-ntp-with-chrony/)
- [Security updates — Ubuntu Security](https://documentation.ubuntu.com/security/security-updates/)
- [Firewall — Ubuntu Security](https://documentation.ubuntu.com/security/security-features/network/firewall/)
- [Unnecessarily open ports — Ubuntu Security](https://documentation.ubuntu.com/security/common-mistakes/unnecessarily-open-ports/)
- [OpenSSH Server banners — Ubuntu Security](https://documentation.ubuntu.com/security/security-features/network/version-banners/openssh-server/)
- [Ubuntu 24.04 LTS release notes](https://documentation.ubuntu.com/release-notes/24.04/)
- [Canonical Kubernetes — configure UFW](https://documentation.ubuntu.com/canonical-kubernetes/latest/snap/howto/networking/ufw/)
- [sshd_config(5) — OpenSSH](https://man.openbsd.org/sshd_config.5)
- [cloud-init Set Passwords / `ssh_pwauth`](https://cloudinit.readthedocs.io/en/latest/reference/modules.html#set-passwords)
- [Launchpad #2088207 — cloud-init sshd_config.d PasswordAuthentication](https://bugs.launchpad.net/cloud-init/+bug/2088207)
- [UFW — Ubuntu Community Help Wiki](https://help.ubuntu.com/community/UFW)
