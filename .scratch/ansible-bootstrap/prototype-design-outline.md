# PROTOTYPE — Ansible bootstrap design outline

> **Superseded.** Real deliverable: [docs/ansible-bootstrap.md](../../docs/ansible-bootstrap.md). Kept as the outline that was reacted to.
> Linked from [.scratch/ansible-bootstrap/issues/10-design-outline-prototype.md](issues/10-design-outline-prototype.md).

---

## 1. Purpose and scope

- One clone of this repo = one environment.
- Ansible (operator machine) takes bare Ubuntu 24.04 VMs → hardened hosts on Netbird → Swarm → verified doco-cd (greenfield), or → Swarm join only (join).
- Does **not** provision VMs, self-host Netbird, deploy Traefik/apps, or retrofit the ephemeral test Swarm.

## 2. Modes

| Mode | Entry | Finish line |
| --- | --- | --- |
| Greenfield | `make greenfield` | doco-cd `1/1` + successful poll/clone; local secrets scrubbed |
| Join | `make join` | New node Ready in Swarm; doco-cd / age / git untouched |

## 3. Operator workflow (secrets)

1. Fill inventory; stage gitignored root files from committed `*.example` siblings: `git_access_token.txt`, `netbird_setup_key.txt`, bootstrap SSH secrets; `make age-key` for `sops_age_key.txt`.
2. Backup age private key offline.
3. Ansible requires explicit backup confirmation before proceeding.
4. After success: scrub staged locals.

Committed: `ssh-keys/` (public keys only), `age.pubkey`, inventory shape (no passwords).

## 4. Inventory schema

Groups: `managers`, `workers`, `new_nodes`.

Per host: `public_ip`, `netbird_ip`, `ansible_host` (public while in `new_nodes`, then Netbird).

Join/greenfield host work targets `new_nodes`. Role = group membership.

### Sketch — `ansible/inventory/hosts.yml`

```yaml
# PROTOTYPE sketch — not real inventory
all:
  children:
    managers:
      hosts:
        mgr1:
          public_ip: 203.0.113.10
          netbird_ip: 100.64.0.2   # filled after enroll
          ansible_host: "{{ public_ip }}"  # then flipped to netbird_ip
          ansible_user: ubuntu
    workers:
      hosts:
        wrk1:
          public_ip: 203.0.113.11
          ansible_host: "{{ public_ip }}"
          ansible_user: root       # provider password path via staged secret file
    new_nodes:
      hosts:
        mgr1:
        wrk1:
```

## 5. Lockdown sequence (per new node)

1. Public SSH → sudo user + repo pubkeys → prove key login → Ansible as that user  
2. Disable password + root SSH  
3. Netbird enroll → record `netbird_ip`  
4. Prove OpenSSH to Netbird IP → flip `ansible_host`, leave `new_nodes`  
5. UFW: allow `wt0` + 80/443, enable (**no** public :22)  
6. Baseline packages  

SSH = normal OpenSSH over mesh.

## 6. Greenfield sequence

Prep → lockdown (all new_nodes) → Docker → swarm init/join (`--advertise-addr` Netbird) → Docker secrets → stack deploy doco-cd → verify → scrub.

Verify: service `1/1`; logs show poll + successful clone; no auth/decrypt loops.

## 7. Join sequence

Add host to managers|workers + new_nodes → lockdown → join-token from existing manager on Netbird → `swarm join` with Netbird advertise-addr → `docker node ls`. Never touch doco-cd / age / git.

## 8. Make + Ansible shape

```
make age-key | greenfield | join

ansible/
  inventory/hosts.yml
  group_vars/all.yml
  playbooks/greenfield.yml
  playbooks/join.yml
  roles/
    bootstrap_user/
    netbird/
    ufw/
    baseline/
    docker/
    swarm/
    doco_cd/          # greenfield only
ssh-keys/
docs/
  ansible-bootstrap.md   # THIS doc when real
  apps.md
  security-policy.md
  research/
apps/
  doco-cd/               # migrate from bootstrap/doco-cd
  traefik/
  arcane/
```

## 9. Docs / repo migration (prescribed)

- Living docs under `docs/`; no day-0/1/2 jargon.
- Root `README.md` always reflects current operator entrypoint.
- `bootstrap/README.md` retires when Ansible path exists; content → `docs/ansible-bootstrap.md`.
- doco-cd → `apps/doco-cd`.

## 10. Open items (still fog / other tickets)

- ~~Default manager quorum~~ → inventory-flexible; odd count note only  
- ~~Netbird setup-key ops~~ → reusable+limit; `.example` files; revoke after run  
- ~~Retire day-N language~~ → `docs/apps.md`  
- Netbird ACL who may SSH  
- Docker Engine channel / pin  

## 11. Out of scope (recap)

VM create, self-hosted Netbird, fail2ban, DNS automation, dual Traefik, apps deploy after verify, implementing Ansible in the design effort.
