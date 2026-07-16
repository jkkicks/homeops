# Ansible bootstrap design

## Destination

A complete Ansible bootstrap **design** for this template repo: overall shape, step sequence, inventory/vars model, greenfield vs join modes, Netbird/Swarm/hardening/doco-cd boundaries, and operator workflow — ready to hand to implementation. This effort produces the plan only; it does not implement Ansible.

**Status: complete** — deliverable [docs/ansible-bootstrap.md](../../docs/ansible-bootstrap.md).

## Notes

- Domain: Swarm GitOps template (`CONTEXT.md`); one environment = one clone of this repo.
- Skills: `/grilling`, `/domain-modeling`; research tickets use `/research`.
- Plan, don't build Ansible in this map unless Notes are later amended.
- Ubuntu **24.04 LTS** only for v1.
- Netbird **cloud** + agents on hosts; no self-hosted Netbird.
- Ansible runs from the **operator machine**.
- Traefik (public/private) is **doco-cd / apps workflow**, not Ansible — only host firewall/Netbird must not block a future private Traefik.
- Design deliverable: `docs/ansible-bootstrap.md` (hardened with verify contracts, SOPS operator secrets, `bootstrap/ansible/` layout). Docs live under `docs/`; doco-cd → `apps/doco-cd`; root README stays current. No day-N jargon.
- Tracker: local markdown under `.scratch/ansible-bootstrap/` (no `docs/agents/issue-tracker.md` yet).

## Decisions so far

- [Docker Swarm control plane over Netbird](issues/02-swarm-over-netbird.md) — Multi-homed nodes must `--advertise-addr` the Netbird IP/`wt0` on init/join; data-path defaults to that; Docker overlay stays for containers, mesh is underlay.
- [Netbird cloud agent enrollment on Ubuntu 24.04](issues/01-netbird-agent-enrollment.md) — APT/`install.sh` + setup-key enroll; `wt0`/`status -4` for IP; verify mesh SSH (ACL + optional UFW `wt0`) before closing public :22.
- [Ubuntu 24.04 practical hardening baseline](issues/03-ubuntu-hardening-baseline.md) — UFW (allow SSH then enable), key-only SSH after proven login (cloud-init drop-in aware), unattended-upgrades + timesyncd; no fail2ban.
- [Inventory and vars schema](issues/04-inventory-and-vars-schema.md) — `managers`/`workers`/`new_nodes`; `public_ip`+`netbird_ip` with `ansible_host` switch; staged secrets + short-lived SSH creds at gitignored repo root; join plays target `new_nodes`.
- [Design deliverable shape](issues/05-design-deliverable-shape.md) — Done = `docs/ansible-bootstrap.md`; docs under `docs/`; doco-cd → `apps/doco-cd`; root README current; rename apps guide; no day-N jargon.
- [SSH and firewall lockdown sequence](issues/06-ssh-firewall-lockdown-sequence.md) — Netbird ASAP after proven key user; UFW (wt0 + 80/443, no public :22) after mesh SSH proof; baseline packages last; OpenSSH over mesh.
- [Greenfield sequence and doco-cd verification](issues/07-greenfield-sequence-and-verification.md) — Prep (make age + tokens + backup confirm) → lockdown → Swarm on Netbird → secrets + stack deploy; verified = doco-cd 1/1 + successful poll/clone; then scrub locals.
- [Join-mode sequence](issues/08-join-mode-sequence.md) — Lockdown new hosts only; join-token from existing manager over Netbird; role = inventory group; never touch doco-cd or age/git secrets.
- [Playbook, role, and make shape](issues/09-playbook-and-make-shape.md) — `make age-key|greenfield|join`; `ansible/playbooks/{greenfield,join}.yml` + roles (`bootstrap_user`…`doco_cd`); `ssh-keys/` for pubkeys.
- [Design outline prototype](issues/10-design-outline-prototype.md) — Outline shape locked; asset [prototype-design-outline.md](prototype-design-outline.md) → promote to `docs/ansible-bootstrap.md` after remaining tickets.
- [Default Swarm manager quorum](issues/11-manager-quorum-default.md) — No fixed manager count; inventory is truth; optional one-liner that Swarm prefers odd counts.
- [Netbird setup key operations](issues/12-netbird-setup-key-ops.md) — Settings→Setup Keys; reusable+limit preferred; `netbird_setup_key.txt` + `.example`; revoke after run; `*.example` for all hand-staged secrets.
- [Retire day-N docs language](issues/13-retire-day-n-docs-language.md) — `docs/apps.md`; living README/bootstrap/validate-layout updated; `docs/superpowers/` left as history.
- [Netbird SSH ACL policy](issues/14-netbird-ssh-acl-policy.md) — Ansible never manages Netbird; per-env group (nodes+operators, full intra-access); all Netbird peers → :80/:443 on nodes.
- [Docker Engine install channel](issues/15-docker-engine-pin.md) — Official Docker CE apt; pin Engine/cli/containerd in group_vars; bump-in-git to upgrade; role optional at implement time.
- [Docs directory layout](issues/16-docs-layout.md) — Flat `docs/`; relative links between pages; no nesting until needed.
- [Write docs/ansible-bootstrap.md](issues/17-write-ansible-bootstrap-design.md) — Deliverable published; map destination complete.

## Not yet specified

<!-- none — destination complete -->

## Out of scope

- Retrofitting the current ephemeral test Swarm
- Self-hosted Netbird management plane
- fail2ban during the bootstrap window
- DNS automation (OpenTofu/Ansible-managed records) for inventory in v1
- Dual Traefik compose, Cloudflare DNS-01, and private ingress app layout (doco-cd / later)
- Provider VM creation / rich cloud-init (assume a bare Ubuntu VM with public SSH)
- Application stack deployment after doco-cd is verified (apps workflow via git)
- Implementing the Ansible tree in this effort
