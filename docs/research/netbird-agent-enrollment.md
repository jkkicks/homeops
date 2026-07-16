# NetBird cloud agent enrollment on Ubuntu 24.04

Research for Ansible-driven bootstrap: install, setup-key enrollment, post-join IP discovery, service management, and constraints for a short public-SSH window then NetBird-only SSH.

Scope: **NetBird Cloud** (managed control plane). Self-hosted management URLs are noted only where docs contrast them.

Primary sources: [docs.netbird.io](https://docs.netbird.io/) (fetched 2026-07-15).

---

## 1. Install methods (Linux / Ubuntu)

Official Linux install paths relevant to Ubuntu 24.04:

### 1.1 One-line install script (documented for servers)

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sh
```

Cited as the install path for cloud VMs and headless peers. The secure-remote-access guide states the script installs the agent and **starts the NetBird service**; afterward you still run `netbird up` (or `netbird up --setup-key …`) to connect. ([Linux Installation](https://docs.netbird.io/get-started/install/linux); [Secure Remote Web Server Access](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access); [Add Servers with Setup Keys](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network))

### 1.2 APT repository (Ubuntu/Debian) — Ansible-friendly

```bash
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg -y
curl -sSL https://pkgs.netbird.io/debian/public.key | sudo gpg --dearmor --output /usr/share/keyrings/netbird-archive-keyring.gpg
echo 'deb [signed-by=/usr/share/keyrings/netbird-archive-keyring.gpg] https://pkgs.netbird.io/debian stable main' | sudo tee /etc/apt/sources.list.d/netbird.list
sudo apt-get update
sudo apt-get install netbird          # CLI only
# optional GUI: sudo apt-get install netbird-ui
```

([Linux Installation — Ubuntu/Debian (APT)](https://docs.netbird.io/get-started/install/linux#ubuntu-debian-apt))

For headless Swarm hosts, install **`netbird`** only (not `netbird-ui`).

### 1.3 Binary + service install

Download a release tarball from GitHub releases, install the binary to `/usr/bin/netbird`, then:

```bash
sudo netbird service install
sudo netbird service start
```

([Linux Installation — Binary Install](https://docs.netbird.io/get-started/install/linux#binary-install); [CLI — service install](https://docs.netbird.io/get-started/cli#service-install))

### 1.4 Docker agent (alternate, not host mesh)

```bash
docker run --network host --privileged --rm -d \
  -e NB_SETUP_KEY=<SETUP KEY> \
  -v netbird-client:/var/lib/netbird \
  netbirdio/netbird:<TAG>
```

Tag must be > 0.6.0. ([Install NetBird — Running with a Setup Key](https://docs.netbird.io/get-started/install#running-net-bird-with-a-setup-key))

**Bootstrap implication:** Prefer APT (or the install script) on the host for a durable systemd unit and overlay interface on the VM itself.

---

## 2. Enrollment: setup keys

### 2.1 What a setup key is

A setup key is a **pre-authentication token** that registers a machine to your NetBird account on first run, without interactive SSO. Docs explicitly call out Ansible/Terraform/CloudFormation-style unattended deploys. ([Register Machines Using Setup Keys](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys))

### 2.2 Create / manage keys

- Dashboard: **Settings → Setup Keys** — create, revoke, set expiration, usage limit, auto-assign groups. ([same](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#managing-setup-keys))
- Alternate: **Peers → Add Peer → Generate Key** — creates a **one-off** key that **expires in 24 hours** with **no auto-assigned groups**. For type/expiration/usage/auto-groups control, use Settings → Setup Keys. ([Create Setup Key](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#create-setup-key))

### 2.3 Key types and options

| Option | Fact | Source |
| --- | --- | --- |
| One-off | Authenticates a single machine once; recommended for security | [Types](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#types-of-setup-keys), [Create](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#create-setup-key) |
| Reusable | Multiple machines; configurable usage limit (default unlimited; docs recommend setting a limit) | [Usage Limit](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#usage-limit) |
| Expiration | Expired keys cannot enroll new peers | [Expiration](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#expiration) |
| Revoke / expire after enroll | Already-authenticated peers **remain connected**; revoke/expire only blocks **new** enrollments | [Managing](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#managing-setup-keys); [Add Servers](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network#creating-a-setup-key-in-your-net-bird-account) |
| Ephemeral peers | Peers enrolled with this option are **removed after >10 minutes offline** — for short-lived workloads, not persistent Swarm nodes | [Ephemeral Peers](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#ephemeral-peers) |
| Auto-assign groups | Peers registered with the key join listed groups (ACL applies automatically); applies to **newly registered** machines only (since v0.9.2) | [Peer Auto-Grouping](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#peer-auto-grouping) |

### 2.4 Enroll command (cloud default)

```bash
netbird up --setup-key <SETUP KEY>
```

- Omitting `--setup-key` prompts interactively. ([Install](https://docs.netbird.io/get-started/install#running-net-bird-with-a-setup-key))
- Default management URL for cloud: `https://api.netbird.io:443` (`-m` / `--management-url`). Self-hosted needs an explicit URL. ([CLI global flags](https://docs.netbird.io/get-started/cli#global-flags))
- `--setup-key-file <path>` — read key from file; ignored if `--setup-key` is set. ([same](https://docs.netbird.io/get-started/cli#global-flags))
- Flags map to `NB_*` env vars (e.g. `NB_SETUP_KEY`, `NB_MANAGEMENT_URL`). ([Environment Variables](https://docs.netbird.io/get-started/cli#environment-variables))
- `netbird login --setup-key …` authenticates without the full `up` flow; `up` is login + connect. ([CLI](https://docs.netbird.io/get-started/cli))

### 2.5 Bundle key at service install

```bash
sudo netbird service install \
  --setup-key AAAA-BBB-CCC-DDDDDD \
  --disable-profiles \
  --disable-update-settings
```

Docs describe this as IT-admin deployment that locks the client to the corporate account. Install parameters persist in `service.json` across uninstall/reinstall unless `netbird service reset-params` + `reconfigure`. ([CLI — service install](https://docs.netbird.io/get-started/cli#service-install))

---

## 3. Interface / IP discovery after join

| Method | Command / location | Source |
| --- | --- | --- |
| WireGuard interface (Linux) | `ip addr show wt0` | [Install — Check your IP](https://docs.netbird.io/get-started/install#running-net-bird-with-a-setup-key); [Linux install](https://docs.netbird.io/get-started/install/linux#running-net-bird-with-a-setup-key) |
| Status summary | `netbird status` — shows `Management`/`Signal`/`Relays`, **FQDN** (e.g. `….netbird.cloud`), **NetBird IP** (e.g. `100.x.x.x/16`), interface type | [Add Servers](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network); [Secure Remote Access](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access) |
| IPv4 only (scriptable) | `netbird status --ipv4` / `-4` — prints only this peer’s NetBird IPv4 | [CLI — status](https://docs.netbird.io/get-started/cli#status) |
| IPv6 only | `netbird status --ipv6` / `-6` | [same](https://docs.netbird.io/get-started/cli#status) |
| Machine-readable | `netbird status --json` / `--yaml`; detail with `-d` | [same](https://docs.netbird.io/get-started/cli#status) |
| Health exit codes | `netbird status -C live\|ready\|startup` — exit 0 success, 1 failure | [same](https://docs.netbird.io/get-started/cli#status) |
| Dashboard | **Peers** — NetBird IP and domain copyable | [Secure Remote Access](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access) |

Overlay addresses are in the NetBird CGNAT-style range (examples use `100.x`); routing-peer docs refer to NetBird IP as the `100.x` overlay address from `netbird status`. ([How Routing Peers Work](https://docs.netbird.io/manage/networks/how-routing-peers-work))

**Ansible wait pattern:** after `netbird up --setup-key`, poll until `netbird status` shows `Management: Connected` (and optionally `netbird status -C ready`), then capture `netbird status -4` and/or FQDN from status/JSON.

---

## 4. Service management

| Concern | Fact | Source |
| --- | --- | --- |
| Unit name | `netbird.service` (systemd) | [Add Servers](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network) |
| Status | `sudo systemctl status netbird` | [same](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network) |
| Enable on boot | `sudo systemctl enable netbird` | [same](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network) |
| CLI service ops | `sudo netbird service install \| uninstall \| start \| stop` (elevated) | [CLI — service](https://docs.netbird.io/get-started/cli#service) |
| Default config path (example) | `/etc/netbird/config.json` in unit ExecStart examples | [Add Servers](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network) |
| Default daemon socket | `unix:///var/run/netbird.sock` | [CLI global flags](https://docs.netbird.io/get-started/cli#global-flags) |
| Default service name flag | `--service netbird` | [same](https://docs.netbird.io/get-started/cli#global-flags) |
| Auto-connect | `--disable-auto-connect` on `up` prevents reconnect when the service starts | [CLI — up flags](https://docs.netbird.io/get-started/cli#flags) |
| Package update | Use apt if installed via package manager; script update: `netbird down` → `./install.sh --update` → `netbird up` | [Linux — Updating](https://docs.netbird.io/get-started/install/linux#updating) |

Install-script path starts the service before enrollment; APT path may still require `service install`/`enable` depending on packaging — verify with `systemctl status netbird` after install (docs show enabled unit after script/server flow).

---

## 5. Constraints for short public SSH → NetBird-only SSH

### 5.1 Two different “SSH over NetBird” models

Docs describe both; do not conflate them:

1. **OpenSSH over the mesh (host `sshd` on TCP 22)**  
   Peers reach each other at NetBird IP/FQDN; Access Control policy allows **TCP port 22** between groups. No inbound internet SSH required after cutover. ([Secure Remote Web Server Access](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access))

2. **Embedded NetBird SSH**  
   Enable with `netbird up --allow-server-ssh`; disabled by default; also requires dashboard SSH enablement and a **NetBird SSH** (or TCP/22) ACL. Clients use `netbird ssh <FQDN|IP>` or OpenSSH with NetBird interception. Requires NetBird **v0.61.0+** for SSH access features as documented. ([SSH Access](https://docs.netbird.io/manage/peers/ssh); [Add Servers — Optional SSH](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network#optional-automating-ssh-access-to-your-vm))

For “host mesh for SSH,” model (1) matches the documented zero-trust server access guide (keep OpenSSH; restrict via NetBird ACL + close public :22). Model (2) is optional and changes the SSH server path (internal 22022 redirection).

### 5.2 Network / firewall facts that affect the bootstrap window

- **Perimeter / cloud SG:** NetBird client needs **no inbound** ports; peers initiate outbound and use ICE/STUN. ([Ports & Firewalls](https://docs.netbird.io/about-netbird/ports-and-firewalls))
- **Outbound (NetBird Cloud):** TCP/443 to `api.netbird.io`, `signal.netbird.io`, `*.relay.netbird.io`; UDP (and related) to `stun.netbird.io` / `turn.netbird.io` (ports documented on that page). Restricted egress without these yields relay/STUN failures in `netbird status`. ([same](https://docs.netbird.io/about-netbird/ports-and-firewalls#outgoing-ports))
- **Host UFW:** Default deny-inbound can conflict with NetBird’s `wt0` rules (chain order). Fix: `sudo ufw allow in on wt0` (does not open internet ports). ([UFW](https://docs.netbird.io/about-netbird/ports-and-firewalls#ufw-linux))
- **ACL prerequisite:** Without an Access Control policy allowing the operator peer/group → server group (e.g. TCP/22), mesh SSH fails even when both peers show Connected. ([Secure Remote Access — policies](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access#2-configuring-net-bird-access-control-policies))
- **`--block-inbound`:** If set on `up`, client blocks inbound to the local machine (overrides management policies) — would break incoming SSH over the mesh. ([CLI — up flags](https://docs.netbird.io/get-started/cli#flags))

### 5.3 Safe cutover sequence (derived from primary facts)

1. Public SSH open only for Ansible bootstrap (assumed greenfield VM).
2. Ensure egress allows NetBird Cloud endpoints ([Ports & Firewalls](https://docs.netbird.io/about-netbird/ports-and-firewalls)).
3. Install agent (APT or install script) and enroll with a **non-ephemeral** setup key (one-off or tightly limited reusable), preferably with **auto-assign groups** that match SSH ACLs. ([Setup keys](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys); [Ephemeral](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#ephemeral-peers))
4. Wait until Management connected; record NetBird IP (`status -4`) / FQDN; confirm peer in dashboard. ([status](https://docs.netbird.io/get-started/cli#status))
5. If UFW will be enabled during hardening, add `allow in on wt0` **before** relying on mesh SSH. ([UFW](https://docs.netbird.io/about-netbird/ports-and-firewalls#ufw-linux))
6. From an already-enrolled operator peer, verify SSH to NetBird IP/FQDN (OpenSSH and/or NetBird SSH per chosen model). ([Secure Remote Access](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access))
7. Only then close public SSH (host firewall / cloud security group). NetBird itself does not require keeping public :22. ([Ports & Firewalls — incoming](https://docs.netbird.io/about-netbird/ports-and-firewalls#incoming-ports))

### 5.4 Operational pitfalls for Ansible

- Setup key must be valid **at enroll time**; expiration after enroll is fine for the peer. ([Add Servers](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network#creating-a-setup-key-in-your-net-bird-account))
- Do **not** use ephemeral keys for persistent hosts (auto-removal after 10 minutes offline). ([Ephemeral](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys#ephemeral-peers))
- Prefer `--setup-key-file` or Ansible vault for secrets rather than shell history. ([CLI](https://docs.netbird.io/get-started/cli#global-flags))
- Closing public SSH before mesh connectivity + ACL + (if used) UFW `wt0` rule is verified strands the operator.

---

## 6. Fact summary for implementers

| Topic | Primary fact |
| --- | --- |
| Install | Ubuntu: APT from `pkgs.netbird.io/debian` or `install.sh`; package `netbird` for CLI |
| Enroll | `netbird up --setup-key …` against cloud default `https://api.netbird.io:443` |
| Interface | Linux overlay iface `wt0` |
| Discover IP | `netbird status` / `netbird status -4` / `ip addr show wt0` |
| Service | systemd `netbird`; `systemctl enable/status`; CLI `netbird service *` |
| Cutover | No inbound ports for NetBird; need outbound control-plane/STUN/TURN; ACL for TCP/22 (or NetBird SSH); UFW needs `allow in on wt0`; verify mesh SSH before dropping public :22 |

---

## Sources

- [Install NetBird](https://docs.netbird.io/get-started/install)
- [Linux Installation](https://docs.netbird.io/get-started/install/linux)
- [NetBird Agent CLI](https://docs.netbird.io/get-started/cli)
- [Register Machines Using Setup Keys](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys)
- [Add Servers to the Network with Setup Keys](https://docs.netbird.io/manage/peers/access-infrastructure/setup-keys-add-servers-to-network)
- [Secure Remote Web Server Access](https://docs.netbird.io/manage/peers/access-infrastructure/secure-remote-webserver-access)
- [SSH Access](https://docs.netbird.io/manage/peers/ssh)
- [Ports & Firewalls](https://docs.netbird.io/about-netbird/ports-and-firewalls)
- [How Routing Peers Work](https://docs.netbird.io/manage/networks/how-routing-peers-work) (overlay IP terminology)
