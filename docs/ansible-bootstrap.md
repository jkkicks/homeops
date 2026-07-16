# Ansible bootstrap design

Design for taking bare Ubuntu 24.04 VMs to a verified doco-cd-managed Swarm over Netbird. **This document is the plan** — the Ansible tree is not implemented yet.

Related: [Apps](apps.md) · [Security policy](security-policy.md) · [Research](research/) · current human checklist [bootstrap/README.md](../bootstrap/README.md)

Wayfinder map (planning index): `.scratch/ansible-bootstrap/map.md`

---

## 1. Purpose and scope

One clone of this repository = one **environment**. Ansible runs on an **operator machine** and:

| Mode | Entry | Finish line |
| --- | --- | --- |
| **Greenfield** | `make greenfield` | Hardened hosts on Netbird, Swarm up, doco-cd verified; long-lived secrets SOPS’d into `bootstrap/ansible/secrets/`; root plaintext deleted |
| **Join** | `make join` | New host joined as manager or worker; **doco-cd / age / git Docker secrets untouched** |
| **Verify** | `make verify` | Completion-contract asserts only (no mutate) |

**In scope:** Ubuntu practical hardening, Netbird agent enrollment, Docker Engine (pinned), Swarm init/join on the host mesh, greenfield Docker secrets + doco-cd deploy, verification contracts, operator `make` + ansible-lint.

**Out of scope:** VM provisioning / rich cloud-init; self-hosted Netbird; fail2ban; DNS automation for inventory; dual Traefik / Cloudflare DNS-01; apps deploy after doco-cd verified; retrofitting the ephemeral test Swarm; Ansible managing the Netbird dashboard; full DevSec/CIS hardening roles.

**OS:** Ubuntu **24.04 LTS** only for v1.

---

## 2. Network model

- **Netbird Cloud** + agents on each host (no self-hosted management plane).
- **Host mesh:** SSH and Swarm control plane / VXLAN underlay use Netbird (`--advertise-addr` / data-path = Netbird IP or `wt0`). See [research/swarm-over-netbird.md](research/swarm-over-netbird.md).
- **Docker overlay networks** remain for container-to-container traffic (e.g. `traefik-public`).
- **Public NIC (UFW after lockdown):** allow **80/443** only. No public SSH. Do **not** publish Swarm ports (2377, 7946 tcp/udp, 4789 udp) on the public interface.
- Private path: Netbird group full access covers SSH + Swarm; UFW `allow in on wt0` (and 80/443 as needed).
- **UFW vs Docker:** both land in iptables. Prefer Swarm/Traefik **ingress publish modes that don’t fight host UFW** — avoid ad-hoc host-mode publishes of conflicting ports from app compose. Traefik’s intentional 80/443 host publish is the public exception.
- **Traefik** is doco-cd / [apps](apps.md) — not Ansible.

### Netbird groups and ACLs (dashboard only)

Ansible **never** creates or edits Netbird groups/ACLs. It only reads a setup key for `netbird up`.

- One **per-environment group** (e.g. `{env}-operators`) in `group_vars`.
- Setup keys auto-assign **nodes**; **operator peers** join the same group.
- **Full access within the group.**
- Extra ACL: any Netbird peer → those nodes **TCP 80/443**.

### Setup keys

- Create under Netbird **Settings → Setup Keys**.
- Prefer reusable + tight usage limit + short expiry; one-off OK for a single host.
- Bootstrap window: gitignored root file from `*.example`; after run, delete (do not SOPS — see §3). Revoke in dashboard when done or leaked.

Research: [research/netbird-agent-enrollment.md](research/netbird-agent-enrollment.md).

---

## 3. Operator secrets workflow

**Decision (locked):** after a successful greenfield (and after any join that introduced new long-lived operator material), Ansible/make **must** SOPS-encrypt the designated long-lived files into `bootstrap/ansible/secrets/`, commit the ciphertext, and **delete** the repo-root plaintext. No “optional” encrypt step.

### Bootstrap-window plaintext (repo root, gitignored)

Hand-created files ship with committed `*.example` siblings (copy → rename → fill):

| File | After successful run |
| --- | --- |
| `sops_age_key.txt` | **Never** committed (not even via SOPS — ciphertext would need the same key to decrypt). Cold offline backup required before greenfield; delete local file after Docker secret exists + encrypt pipeline for other secrets. |
| `git_access_token.txt` | **SOPS →** `bootstrap/ansible/secrets/git_access_token.sops.yml` (or `.enc.txt`), **tracked in git**, then delete root plaintext |
| `netbird_setup_key.txt` | **Delete only** — do not archive in git (keys are batch-scoped and revoked; next join stages a fresh key from `.example`) |
| Bootstrap SSH secrets | **Delete only** — minutes-lived; useless after lockdown |

Committed non-secrets: root `ssh-keys/` (**public** keys only), `age.pubkey`, inventory.

Ansible requires explicit age-backup confirmation before greenfield. Use `no_log: true` on tasks that touch setup keys, tokens, passwords, or Swarm join tokens.

### Long-lived operator secrets (SOPS) — tracked ciphertext

Path: **`bootstrap/ansible/secrets/`** — **committed** SOPS ciphertext only (same model as `apps/*/secrets/*.enc.*`). Plaintext never lives there; directory is not gitignored for `*.sops.yml` / `*.enc.*`.

- Same environment age public key as [security-policy.md](security-policy.md) / `.sops.yaml`.
- Decrypt on the operator machine only when needed (recreate Docker secret, etc.), using the cold age private key briefly — then remove plaintext again.
- Greenfield reads bootstrap-window root files first; later runs may read from SOPS under `bootstrap/ansible/secrets/` when root plaintext is gone.

Swarm **join tokens** are never stored in git or SOPS — always fetched at runtime from a live manager.

---

## 4. Inventory schema

One inventory per environment, under `bootstrap/ansible/`.

**Groups**

- `managers` / `workers` — Swarm role (every host in exactly one)
- `new_nodes` — bootstrap window; remove after Netbird lockdown

No separate `initial_swarm_manager` group. **Init target** = first host in `managers` (document order in `hosts.yml`). Trivial override via a single optional var (`swarm_init_host`) only if implementation stays one-liner; do not invent a dedicated role for this.

**Host vars**

| Var | Purpose |
| --- | --- |
| `public_ip` | Provider address for bootstrap window |
| `netbird_ip` | Filled after enroll |
| `ansible_host` | `public_ip` while in `new_nodes`; then `netbird_ip` |
| `hostname` | Desired hostname (inventory-defined) |
| `ansible_user` | Initial / permanent user shape |
| `swarm_labels` | Optional node labels (default none) |
| `swarm_availability` | Default **`active`** for managers and workers (host services). Optional override (e.g. `drain`) for future use — not the default |

**Timezone:** UTC for all hosts (`group_vars`), overridable only if explicitly needed.

**Manager count:** inventory is truth (1, 3, 5, …); odd counts preferred for Raft.

**Join scoping:** plays that mutate new hosts target `new_nodes`. Join tokens from an existing manager on Netbird.

### Example shape

```yaml
all:
  children:
    managers:
      hosts:
        mgr1:
          hostname: mgr1
          public_ip: 203.0.113.10
          netbird_ip: 100.64.0.2
          ansible_host: "{{ public_ip }}"
          ansible_user: ubuntu
    workers:
      hosts:
        wrk1:
          hostname: wrk1
          public_ip: 203.0.113.11
          ansible_host: "{{ public_ip }}"
          ansible_user: root
    new_nodes:
      hosts:
        mgr1:
        wrk1:
```

---

## 5. Lockdown sequence (per new node)

Netbird ASAP; normal **OpenSSH over the mesh**.

1. Connect over public SSH (provider key or root password).
2. Create permanent admin/automation user → install pubkeys → **passwordless sudo** → lock account password → **prove** key login → Ansible uses that user.
3. Disable password auth and root SSH (still public, key-only).
4. Install/enroll Netbird (skip enroll if already connected); record `netbird_ip`; set hostname; ensure UTC.
5. Prove OpenSSH to `netbird_ip` → flip `ansible_host`, leave `new_nodes`.
6. UFW: `allow in on wt0`, allow public `80`/`443`, enable — **no** public OpenSSH; Swarm ports not on public NIC.
7. Practical baseline packages (unattended-upgrades, timesyncd, etc.) — **not** full DevSec/CIS.

Research: [research/ubuntu-hardening-baseline.md](research/ubuntu-hardening-baseline.md), [research/netbird-agent-enrollment.md](research/netbird-agent-enrollment.md).

---

## 6. Greenfield sequence

1. Prep: inventory + staged secrets + `make age-key` + backup confirm + commit `age.pubkey` / `.sops.yaml`.
2. Lockdown on all `new_nodes` (§5), with **serial: 1** for managers when applying network/Docker restarts.
3. Docker CE (official apt), **pinned** in `group_vars`; configure conservative `daemon.json` (log rotation, no unauthenticated remote TCP API, live-restore, etc.). Prefer `geerlingguy.docker` (or equivalent) + thin local policy role if pins work.
4. Swarm: first `managers` host inits with Netbird advertise/data-path; others join via runtime tokens (`community.docker` preferred). Fail if a host is already in a **different** Swarm.
5. doco-cd: create Docker secrets; deploy from **`apps/doco-cd/compose.yaml`** only (no duplicate compose in the role). Move from `bootstrap/doco-cd/` as part of implementation.
6. Run completion contract (§11).
7. **Required:** SOPS-encrypt `git_access_token` into `bootstrap/ansible/secrets/`, commit ciphertext; delete root plaintext (age key + Netbird setup key + SSH bootstrap secrets deleted per §3 — age key never SOPS’d into git).
8. Later Ansible runs: **do not** fight doco-cd — verify/restore stack only if missing; no routine redeploy.

---

## 7. Join sequence

1. Existing managers on Netbird.
2. Add host to `managers`|`workers` + `new_nodes`; stage SSH + Netbird setup key. Do not rotate age/git Docker secrets.
3. Lockdown (§5).
4. Fetch join token from live manager at runtime (`no_log`); join with Netbird advertise-addr.
5. **Manager-confirmed** Ready/role/availability (local state alone is insufficient). Apply optional labels; availability defaults to `active`.

---

## 8. Operator machine checklist

Documented here and to be mirrored in `bootstrap/ansible/README.md` when Ansible ships. Before `make greenfield` / `make join`:

1. **Clone** this environment repo; operator machine can reach new hosts’ **public SSH** (key or password as inventoried).
2. **Netbird:** operator peer enrolled in Netbird Cloud and in the environment group (e.g. `{env}-operators`) so mesh SSH works after cutover.
3. **Tools on the operator machine:**
   - Ansible (control node)
   - `ansible-lint`
   - `age` / `sops` (for `make age-key` and `bootstrap/ansible/secrets/`)
   - Docker CLI optional (for context against a manager over SSH after Swarm exists)
4. **Inventory** filled (`managers` / `workers` / `new_nodes`, `public_ip`, `hostname`, SSH shape).
5. **Root `ssh-keys/`** contains the public keys to install.
6. **Staged secrets** from `*.example`: `git_access_token.txt`, `netbird_setup_key.txt`, bootstrap SSH secrets as needed; `make age-key` for `sops_age_key.txt` + **cold backup** of the age private key.
7. **Netbird dashboard:** setup key with auto-group + ACLs per §2 (full access in env group; :80/:443 from other Netbird peers).
8. After greenfield: confirm SOPS ciphertext under `bootstrap/ansible/secrets/` is committed and root plaintext is gone.

Install Galaxy deps once: `ansible-galaxy install -r bootstrap/ansible/requirements.yml` (pinned).

---

## 9. Pinned Docker versions (Ubuntu 24.04 / noble)

Aligned with current Docker Engine **29.6.1** / containerd **2.2.5** (operator Desktop reference; server packages from Docker’s official apt). Bump these in `group_vars` intentionally when upgrading:

| Package | Pin (noble amd64/arm64 apt) |
| --- | --- |
| `docker-ce` | `5:29.6.1-1~ubuntu.24.04~noble` |
| `docker-ce-cli` | `5:29.6.1-1~ubuntu.24.04~noble` |
| `containerd.io` | `2.2.5-1~ubuntu.24.04~noble` |
| `docker-buildx-plugin` | `0.35.0-1~ubuntu.24.04~noble` |
| `docker-compose-plugin` | `5.3.1-1~ubuntu.24.04~noble` |

Put these exact strings in `bootstrap/ansible/group_vars/all.yml` at implement time. `requirements.yml` pins Ansible collections/roles to exact versions after first successful test.

---

## 10. Make, layout, and tooling

Ansible lives under **`bootstrap/`** (bootstrap concern; future IaC gets its own top-level area). Flatten inside `bootstrap/` as needed; prescribed tree:

```text
make age-key | greenfield | join | verify | lint

bootstrap/
  ansible/
    ansible.cfg
    requirements.yml          # pin collections/roles (e.g. community.docker, optional geerlingguy.docker)
    inventory/hosts.yml
    group_vars/all.yml
    secrets/                  # committed SOPS ciphertext only (e.g. git_access_token)
    playbooks/
      greenfield.yml
      join.yml
      verify.yml              # asserts only
    roles/
      bootstrap_user/
      netbird/
      ufw/
      baseline/
      docker/
      swarm/
      doco_cd/                # greenfield path; compose from apps/doco-cd
      verify/
  README.md                   # short operator pointer (replaces long checklist when Ansible ships)
apps/
  doco-cd/                    # migrated from bootstrap/doco-cd
ssh-keys/                     # repo root — committed public keys only
```

- Prefer Ansible modules over shell; handlers for restarts.
- Coarse tags OK for debugging (`netbird`, `docker`, `swarm`, `verify`) — entrypoints remain the three playbooks + make.
- **`make lint`:** `ansible-lint` (+ `ansible-playbook --syntax-check`) wired in `scripts/` or Makefile; extend [validate-layout.sh](../scripts/validate-layout.sh) or sibling script as needed.

### Serial / blast radius

- Greenfield: init manager alone first when multi-node.
- Additional managers: `serial: 1`.
- Docker/network/reboot affecting managers: one at a time.
- Workers: default `serial: 1` until proven; then cautious batches.

---

## 11. Completion contracts

Tasks succeeding is not enough — `verify` role uses explicit asserts. Fail the play with a specific requirement name.

### Greenfield / first cluster

- Ubuntu 24.04; unattended-upgrades + timesyncd (UTC); hostname applied.
- Automation user exists; password locked; passwordless sudo; key SSH works; password + root SSH disabled.
- Public :22 closed; OpenSSH works via Netbird.
- Netbird installed, connected, private IP present.
- UFW default deny inbound; public allows 80/443 only; Swarm ports not public.
- Docker installed (pinned versions), enabled; no open unauthenticated Docker TCP API; log rotation configured.
- Swarm active; advertise/data-path private; init manager Ready; other nodes Ready as declared.
- doco-cd stack present, desired replicas up; logs show successful poll/clone; no auth/decrypt loops.
- Second `make greenfield` / verify run is idempotent (no unintended changes).

### Join

- Same host hardening/SSH/Netbird/UFW/Docker bars as above (as applicable).
- Existing manager reports node present, expected role, **Ready**, availability (default active), optional labels.
- Not a member of a different Swarm.
- Second `make join` / verify run is idempotent.
- doco-cd not redeployed.

---

## 12. Idempotency and failure behavior

- NetBird enroll only if not already registered/connected.
- Swarm init only if designated init host is inactive.
- Swarm join only if not already in **this** cluster; **fail** if in another.
- Join tokens: runtime only, `no_log`, never git.
- doco-cd: bootstrap once; later runs verify/restore-if-absent only.
- Handlers restart services only on real config change.
- Verification failures are hard fails with clear messages.

---

## 13. Docs and repo migration

Flat `docs/` with relative links ([ansible-bootstrap](ansible-bootstrap.md), [apps](apps.md), [security-policy](security-policy.md), [research/](research/)).

- Root [README.md](../README.md) always reflects **current** entrypoint.
- When Ansible ships: thin `bootstrap/README.md` → pointer into `bootstrap/ansible/` + this doc; doco-cd under `apps/doco-cd/`.
- No day-N jargon.

---

## 14. Implementation handoff

1. Skeleton: Makefile, `bootstrap/ansible/`, `requirements.yml`, examples, gitignore, ansible-lint target.
2. `bootstrap_user` + netbird + ufw + baseline; prove single-node cutover.
3. Docker (pinned + daemon.json) + Swarm init/join (`community.docker`) + serial behavior.
4. `doco_cd` from `apps/doco-cd` + required SOPS into `bootstrap/ansible/secrets/` + delete root plaintext.
5. `verify` playbook + greenfield/join contracts; idempotent second runs.
6. README / docs cutover; remove obsolete long human checklist steps.

Until then, live path remains [bootstrap/README.md](../bootstrap/README.md) (Swarm already exists).
