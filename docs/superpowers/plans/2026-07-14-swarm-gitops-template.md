# Swarm GitOps Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reshape this repo into the approved Swarm GitOps template: bootstrap doco-cd, SOPS+age secrets → Docker secrets, Arcane as a normal git-managed app, and docs/runbooks for day-2 ops.

**Architecture:** One clone = one Swarm environment. Humans bootstrap once (age private key + git credentials as Docker secrets, then `docker stack deploy` doco-cd). doco-cd polls this repo, decrypts SOPS, auto-discovers `apps/*`, and deploys Swarm stacks (including secret rotation). Arcane lives under `apps/`; doco-cd stays under `bootstrap/` and may self-update from git when safe.

**Tech Stack:** Docker Swarm, doco-cd (`ghcr.io/kimdre/doco-cd`), SOPS + age, Compose v3 stack files, shell layout validation script.

**Spec:** `docs/superpowers/specs/2026-07-14-swarm-gitops-template-design.md`

---

## File structure (target)

| Path | Responsibility |
| --- | --- |
| `README.md` | Clone overview + pointer to bootstrap |
| `.gitignore` | Ignore plaintext secrets, age private keys, `.superpowers/` |
| `.sops.yaml` | Creation rules pointing at cluster age public key |
| `age.pubkey` | Committed age public key for this environment (placeholder until bootstrap) |
| `.doco-cd.yaml` | Deploy configs: self-manage `bootstrap/doco-cd`, auto-discover `apps/` |
| `bootstrap/README.md` | Human one-time checklist + recovery (redeploy CD, restore age key) |
| `bootstrap/doco-cd/compose.yaml` | doco-cd Swarm stack (socket, secrets, poll config) |
| `bootstrap/doco-cd/poll-config.yaml` | Poll this repo (URL/ref/interval); committed with placeholders |
| `bootstrap/doco-cd/secrets/README.md` | How bootstrap secrets are encrypted / what is external |
| `apps/arcane/compose.yaml` | Arcane stack using file-based secrets (not `external: true`) |
| `apps/arcane/secrets/*.enc` | SOPS-encrypted secret payloads (or `.gitkeep` + encrypt instructions until real values exist) |
| `apps/arcane/secrets/README.md` | How to create/rotate Arcane secrets |
| `docs/security-policy.md` | Short security policy from the vision |
| `docs/day-2-apps.md` | Add/change/rotate app workflow |
| `scripts/validate-layout.sh` | Repo structure + “no plaintext secret smell” checks |
| Delete after migrate | `REAMDE.MD`, `apps/arcane.yaml` (plaintext secrets!), `apps/arcane-swarm.yaml`, `secrets/bootstrap.md` |

---

### Task 1: Layout validator + gitignore hygiene

**Files:**
- Create: `scripts/validate-layout.sh`
- Modify: `.gitignore`
- Delete (later task; do not delete yet): legacy paths still present until Task 6–7

- [x] **Step 1: Write the validator (failing until layout exists)**

Create `scripts/validate-layout.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

need() {
  [[ -e "$1" ]] || fail "missing required path: $1"
  ok "found $1"
}

need "README.md"
need ".sops.yaml"
need "age.pubkey"
need ".doco-cd.yaml"
need "bootstrap/README.md"
need "bootstrap/doco-cd/compose.yaml"
need "bootstrap/doco-cd/poll-config.yaml"
need "apps/arcane/compose.yaml"
need "docs/security-policy.md"
need "docs/day-2-apps.md"

# Forbid known plaintext secret dumps
if [[ -f "apps/arcane.yaml" ]]; then
  fail "apps/arcane.yaml must be removed (contained plaintext secrets)"
fi

# Smell test: no ENC[-looking] plaintext KEY= with common secret names in tracked compose without .enc
if git ls-files '*.yaml' '*.yml' '*.env' 2>/dev/null | xargs grep -nE '^(JWT_SECRET|ENCRYPTION_KEY|POSTGRES_PASSWORD|DATABASE_URL)=' 2>/dev/null | grep -v '\.enc\.' ; then
  fail "possible plaintext secret assignment in tracked files"
else
  ok "no obvious plaintext secret assignments in tracked env-style files"
fi

# Private age key must not be committed
if git ls-files | grep -E '(^|/ )?(sops_age_key\.txt|age-key\.txt|\.age-key)$' ; then
  fail "age private key file appears tracked by git"
else
  ok "no tracked age private key filenames"
fi

echo "All layout checks passed."
```

- [x] **Step 2: Make executable and run (expect FAIL)**

```bash
chmod +x scripts/validate-layout.sh
./scripts/validate-layout.sh
```

Expected: `FAIL: missing required path: README.md` (or first missing path).

- [x] **Step 3: Extend `.gitignore`**

Ensure `.gitignore` contains at least:

```gitignore
.superpowers/

# Never commit decrypt material or local plaintext
sops_age_key.txt
age-key.txt
*.agekey
**/secrets/*.plain.*
**/secrets/*.dec.*
**/*.dec.yaml
**/*.dec.env
```

- [x] **Step 4: Commit**

```bash
git add scripts/validate-layout.sh .gitignore
git commit -m "$(cat <<'EOF'
chore: add repo layout validator and tighten gitignore

EOF
)"
```

---

### Task 2: Root README + SOPS/age public config stubs

**Files:**
- Create: `README.md`
- Create: `.sops.yaml`
- Create: `age.pubkey`
- Delete: `REAMDE.MD` (typo filename)

- [x] **Step 1: Add placeholder `age.pubkey`**

```text
# REPLACE during bootstrap with: age-keygen -y sops_age_key.txt
# Example format only — not a real key:
age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- [x] **Step 2: Add `.sops.yaml`**

```yaml
creation_rules:
  - path_regex: .*\.(enc\.)?(yaml|yml|env|txt)$
    encrypted_regex: ".*"
    # Replace with the real public key from age.pubkey after bootstrap
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Note: after real bootstrap, both `age.pubkey` and `.sops.yaml` must use the same real public key. Until then placeholders are intentional; document that encryption will fail until replaced.

- [x] **Step 3: Write `README.md`**

```markdown
# Swarm GitOps Template

One clone of this repository = one Docker Swarm environment.

Git is the desired-state source of truth. [doco-cd](https://doco.cd/) polls this repo, decrypts [SOPS](https://getsops.io/) secrets, and deploys Swarm stacks. Runtime secrets live as **Docker secrets**. [Arcane](https://getarcane.app/) is the management UI — not a second source of truth.

## Quick start

1. Swarm already initialized (node IaC is out of scope here).
2. Follow **[bootstrap/README.md](bootstrap/README.md)** (age key, git credentials, first doco-cd deploy).
3. Add workloads under `apps/<name>/` — see [docs/day-2-apps.md](docs/day-2-apps.md).

## Layout

- `bootstrap/` — human one-time steps + doco-cd
- `apps/` — Arcane and all other stacks
- `docs/` — security policy and day-2 guides
- Spec: `docs/superpowers/specs/2026-07-14-swarm-gitops-template-design.md`

## Validate

```bash
./scripts/validate-layout.sh
```
```

- [x] **Step 4: Remove typo README**

```bash
git rm -f REAMDE.MD
```

- [x] **Step 5: Commit**

```bash
git add README.md .sops.yaml age.pubkey
git commit -m "$(cat <<'EOF'
docs: add root README and SOPS/age stubs; remove typo REAMDE

EOF
)"
```

---

### Task 3: Security policy + day-2 docs

**Files:**
- Create: `docs/security-policy.md`
- Create: `docs/day-2-apps.md`

- [x] **Step 1: Write `docs/security-policy.md`**

Content must include (full file):

```markdown
# Security policy

## Runtime

- Docker secrets are the runtime system of truth for secret values.
- Services consume secrets via Swarm secret mounts / `*_FILE` paths under `/run/secrets/`.

## Git

- Only SOPS ciphertext is committed for secret values.
- Age **public** key and `.sops.yaml` are committed so operators can encrypt.
- Age **private** key is never committed. It exists as a Docker secret on managers and as an offline backup (e.g. Vaultwarden) for recovery only.

## Bootstrap chicken-and-egg

Human creates:

1. Age private key → Docker secret (e.g. `sops_age_key`)
2. Git credential → Docker secret (e.g. `git_access_token`) for first doco-cd deploy
3. Deploys `bootstrap/doco-cd`

After that, app secrets are managed from encrypted files in git via doco-cd.

## Forbidden

- Plaintext secrets in git
- Treating Arcane as durable desired state outside git
- Long-term reliance on plaintext bind-mounted secret files when Docker secrets can be used
```

- [x] **Step 2: Write `docs/day-2-apps.md`**

```markdown
# Day-2: apps

## Add an app

1. Create `apps/<name>/compose.yaml` (Swarm-compatible compose).
2. Put secret payloads under `apps/<name>/secrets/` and encrypt with SOPS using the cluster public key in `age.pubkey` / `.sops.yaml`.
3. Reference secret files from compose (`secrets:` → `file: ./secrets/...`).
4. Commit and push. doco-cd auto-discovers directories under `apps/` (see `.doco-cd.yaml`).

## Change a service

Edit compose → commit → push. doco-cd reconciles the stack.

## Rotate a secret

1. `sops edit apps/<name>/secrets/<file>` (or re-encrypt).
2. Commit and push. doco-cd rotates Docker secrets (content hash suffix) and redeploys consumers.

## Observe

Use Arcane and `docker` CLI. Durable fixes still go through git.
```

- [x] **Step 3: Commit**

```bash
git add docs/security-policy.md docs/day-2-apps.md
git commit -m "$(cat <<'EOF'
docs: add security policy and day-2 app guide

EOF
)"
```

---

### Task 4: bootstrap/doco-cd stack + bootstrap runbook

**Files:**
- Create: `bootstrap/README.md`
- Create: `bootstrap/doco-cd/compose.yaml`
- Create: `bootstrap/doco-cd/poll-config.yaml`
- Create: `bootstrap/doco-cd/secrets/README.md`

- [x] **Step 1: Write `bootstrap/doco-cd/poll-config.yaml`**

```yaml
# Replace url with this clone's Git remote. reference must match the branch you deploy from.
- url: https://github.com/EXAMPLE/homeops.git
  reference: refs/heads/main
  interval: 60s
```

- [x] **Step 2: Write `bootstrap/doco-cd/compose.yaml`**

Use Swarm-oriented compose. Age key and git token are **external** Docker secrets for first deploy (and steady state for decrypt/auth). Poll config is a repo file bind/config — for Swarm, prefer a config from file content committed in-repo so self-update works:

```yaml
version: "3.9"

services:
  doco-cd:
    image: ghcr.io/kimdre/doco-cd:latest
    environment:
      TZ: UTC
      SOPS_AGE_KEY_FILE: /run/secrets/sops_age_key
      GIT_ACCESS_TOKEN_FILE: /run/secrets/git_access_token
      POLL_CONFIG_FILE: /poll-config.yaml
      # Swarm features on by default when daemon is in Swarm mode
    secrets:
      - source: sops_age_key
        target: sops_age_key
      - source: git_access_token
        target: git_access_token
    configs:
      - source: poll_config
        target: /poll-config.yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - doco-cd-data:/data
    networks:
      - doco-cd
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      restart_policy:
        condition: on-failure
      labels:
        cloud.subtract.application: "doco-cd"
        cloud.subtract.environment: "production"
        cloud.subtract.managed-by: "bootstrap"
        cloud.subtract.provisioning-source: "git"

volumes:
  doco-cd-data:
    driver: local
    labels:
      cloud.subtract.application: "doco-cd"

networks:
  doco-cd:
    driver: overlay
    attachable: true

secrets:
  sops_age_key:
    external: true
  git_access_token:
    external: true

configs:
  poll_config:
    file: ./poll-config.yaml
```

If Swarm `configs.file` relative paths prove awkward on first `docker stack deploy`, the bootstrap README must document copying/using `--compose-file` from the checked-out path on the manager (see Step 4).

- [x] **Step 3: Write `bootstrap/doco-cd/secrets/README.md`**

```markdown
# bootstrap/doco-cd secrets

## External (human bootstrap — Docker secrets)

| Docker secret name   | Contents                          |
| -------------------- | --------------------------------- |
| `sops_age_key`       | Age private key file contents     |
| `git_access_token`   | Git HTTPS token / PAT for polling |

These stay external so the first deploy and SOPS decrypt never require ciphertext the agent cannot yet read.

## Optional later

Additional encrypted files for doco-cd may be added here once SOPS decrypt is proven; prefer keeping chicken-and-egg credentials external.
```

- [x] **Step 4: Write `bootstrap/README.md`** (full checklist)

Must cover:

1. Confirm `docker info` shows Swarm active / this node is a manager.
2. `age-keygen -o sops_age_key.txt` → backup private key offline → `age-keygen -y sops_age_key.txt > age.pubkey` → update committed `age.pubkey` and `.sops.yaml` → commit.
3. `docker secret create` for `sops_age_key` and `git_access_token` with labels (`cloud.subtract.*`).
4. Edit `poll-config.yaml` URL/branch to this remote; commit if needed.
5. From a manager with this repo checked out:

```bash
docker stack deploy -c bootstrap/doco-cd/compose.yaml doco-cd
```

6. Verify: `docker service ls`, doco-cd logs, first poll succeeds.
7. **Recovery:** how to redeploy doco-cd manually if self-update breaks it (same stack deploy command).
8. **Lost age key:** restore from offline backup into a new/updated Docker secret workflow (note: Swarm secrets are immutable — create new secret name or remove stack/secret carefully; document the safe path).

Include label examples matching existing style:

```bash
openssl rand -hex 0 >/dev/null 2>&1 # no-op guard for copy/paste blocks
docker secret create \
  --label cloud.subtract.application=doco-cd \
  --label cloud.subtract.environment=production \
  --label cloud.subtract.managed-by=manual \
  --label cloud.subtract.provisioning-source=bootstrap \
  --label cloud.subtract.purpose=sops-age-private-key \
  sops_age_key - < sops_age_key.txt
```

(Use `printf`/`cat` redirection as appropriate; never echo secrets into shell history carelessly — prefer `docker secret create ... < file` then shred local file after offline backup.)

- [x] **Step 5: Commit**

```bash
git add bootstrap/
git commit -m "$(cat <<'EOF'
feat: add doco-cd bootstrap stack and human runbook

EOF
)"
```

---

### Task 5: Root `.doco-cd.yaml` (self-update + apps auto-discovery)

**Files:**
- Create: `.doco-cd.yaml`

- [x] **Step 1: Create `.doco-cd.yaml`**

```yaml
# Deployment 1: keep doco-cd itself in sync from bootstrap/
- name: doco-cd
  working_dir: bootstrap/doco-cd
  compose_files:
    - compose.yaml
  remove_orphans: true

# Deployment 2: every apps/<dir> with a compose file becomes a stack
- name: apps
  working_dir: apps
  auto_discovery:
    enabled: true
    depth: 1
    delete: true
    remove_volumes: false
    remove_images: true
```

Note: If doco-cd self-update of a stack that mounts the Docker socket is considered too risky during implementation, set a short comment in `.doco-cd.yaml` and temporarily remove the first deployment — but the **default plan is to enable self-update** per the vision, with recovery documented in `bootstrap/README.md`.

- [x] **Step 2: Commit**

```bash
git add .doco-cd.yaml
git commit -m "$(cat <<'EOF'
feat: configure doco-cd deployments for bootstrap and apps/*

EOF
)"
```

---

### Task 6: Migrate Arcane to `apps/arcane` with file-based secrets

**Files:**
- Create: `apps/arcane/compose.yaml`
- Create: `apps/arcane/secrets/README.md`
- Create: `apps/arcane/secrets/.gitkeep` (until real `.enc` files exist)
- Delete: `apps/arcane.yaml`, `apps/arcane-swarm.yaml`

**Important:** Existing `apps/arcane.yaml` contains **plaintext secrets**. Remove it from git history awareness going forward; after delete, **rotate** any credentials that were ever committed (JWT, encryption key, DB password) as a mandatory ops note in the secrets README.

- [x] **Step 1: Write `apps/arcane/compose.yaml`**

Base on current `apps/arcane-swarm.yaml`, but change secrets from `external: true` to **file-backed** so doco-cd can decrypt SOPS and create/rotate Swarm secrets:

```yaml
version: "3.9"

services:
  arcane:
    image: ghcr.io/getarcaneapp/manager:latest
    ports:
      - target: 3552
        published: 3552
        protocol: tcp
        mode: ingress
    environment:
      APP_URL: "https://CHANGE_ME:3552"
      PUID: "1000"
      PGID: "1000"
      LOG_LEVEL: "info"
      LOG_JSON: "false"
      OIDC_ENABLED: "false"
      PROJECTS_DIRECTORY: "/opt/stacks"
      ENCRYPTION_KEY__FILE: "/run/secrets/arcane_encryption_key"
      JWT_SECRET__FILE: "/run/secrets/arcane_jwt_secret"
      DATABASE_URL__FILE: "/run/secrets/arcane_database_url"
    secrets:
      - source: arcane_encryption_key
        target: arcane_encryption_key
        uid: "1000"
        gid: "1000"
        mode: 0400
      - source: arcane_jwt_secret
        target: arcane_jwt_secret
        uid: "1000"
        gid: "1000"
        mode: 0400
      - source: arcane_database_url
        target: arcane_database_url
        uid: "1000"
        gid: "1000"
        mode: 0400
    volumes:
      - arcane-data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
      - /opt/stacks:/opt/stacks
    networks:
      - arcane
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      restart_policy:
        condition: on-failure
      labels:
        cloud.subtract.application: "arcane"
        cloud.subtract.environment: "production"
        cloud.subtract.managed-by: "doco-cd"
        cloud.subtract.provisioning-source: "git"

volumes:
  arcane-data:
    driver: local
    labels:
      cloud.subtract.application: "arcane"

networks:
  arcane:
    driver: overlay
    attachable: true

secrets:
  arcane_encryption_key:
    file: ./secrets/encryption_key.enc.txt
  arcane_jwt_secret:
    file: ./secrets/jwt_secret.enc.txt
  arcane_database_url:
    file: ./secrets/database_url.enc.txt
```

doco-cd will decrypt `*.enc.txt` in place before creating Swarm secrets (content must include SOPS markers). Filenames must keep a correct extension for SOPS format (`txt` = binary/text mode is fine for raw secret strings).

- [x] **Step 2: Write `apps/arcane/secrets/README.md`**

Document generating values, encrypting after real `age.pubkey` is set:

```bash
# After bootstrap updated age.pubkey / .sops.yaml:
umask 077
openssl rand -hex 32 > /tmp/arcane_encryption_key.plain
openssl rand -hex 32 > /tmp/arcane_jwt_secret.plain
# database_url: paste real URL into /tmp/arcane_database_url.plain

sops encrypt --age "$(cat age.pubkey | grep -v '^#' | head -1)" \
  /tmp/arcane_encryption_key.plain > apps/arcane/secrets/encryption_key.enc.txt
# repeat for jwt + database_url
shred -u /tmp/arcane_*.plain
```

State clearly: **rotate any secrets that appeared in the old `apps/arcane.yaml`.**

- [x] **Step 3: Add `.gitkeep` under secrets until encrypted files are added**

```bash
mkdir -p apps/arcane/secrets
touch apps/arcane/secrets/.gitkeep
```

When encrypted files are created, remove `.gitkeep` if desired.

- [x] **Step 4: Delete legacy app files**

```bash
git rm -f apps/arcane.yaml apps/arcane-swarm.yaml
```

- [x] **Step 5: Commit**

```bash
git add apps/arcane/
git commit -m "$(cat <<'EOF'
feat: move Arcane under apps/ with SOPS file-backed secrets

Remove legacy compose drafts that included plaintext credentials.
Rotate any secrets that were previously committed.

EOF
)"
```

---

### Task 7: Retire old secrets bootstrap notes; wire validator green

**Files:**
- Delete: `secrets/bootstrap.md` (content superseded by `bootstrap/README.md`)
- Remove empty `secrets/` dir if unused
- Modify: `scripts/validate-layout.sh` if any path tweaks needed

- [x] **Step 1: Remove legacy secrets folder content**

```bash
git rm -f secrets/bootstrap.md
# if secrets/commands.txt exists and is local-only / sensitive, do not commit it; add to gitignore if needed
```

If `secrets/commands.txt` is untracked scratch, ensure `.gitignore` has `secrets/commands.txt` or delete locally after migrating useful bits into `bootstrap/README.md`.

- [x] **Step 2: Run validator**

```bash
./scripts/validate-layout.sh
```

Expected: `All layout checks passed.`

If Arcane encrypted secret files are still missing, either:

- relax validator to require `apps/arcane/secrets/README.md` + `.gitkeep` instead of the three `.enc.txt` files until bootstrap encryption is done, **or**
- create **dummy** SOPS-encrypted placeholders only after a real age key exists.

**Preferred:** update validator to require README + (either the three `.enc.txt` files **or** `.gitkeep`) so the repo stays green before live secrets exist:

```bash
need "apps/arcane/secrets/README.md"
if [[ ! -f apps/arcane/secrets/encryption_key.enc.txt ]]; then
  need "apps/arcane/secrets/.gitkeep"
  ok "arcane secrets pending encryption (.gitkeep present)"
else
  need "apps/arcane/secrets/encryption_key.enc.txt"
  need "apps/arcane/secrets/jwt_secret.enc.txt"
  need "apps/arcane/secrets/database_url.enc.txt"
fi
```

- [x] **Step 3: Re-run validator — expect PASS**

- [x] **Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: retire legacy secrets notes; make layout validator pass

EOF
)"
```

---

### Task 8: End-to-end bootstrap dry-run checklist (on Swarm)

**Files:**
- Modify: `bootstrap/README.md` (add “Verification” section if anything learned)

This task is executed on a real Swarm manager (homelab), not only in git.

- [ ] **Step 1: Generate real age key; update `age.pubkey` + `.sops.yaml`; commit**

- [ ] **Step 2: Create Docker secrets `sops_age_key` and `git_access_token`**

- [ ] **Step 3: Fix `poll-config.yaml` remote URL; commit/push**

- [ ] **Step 4: `docker stack deploy -c bootstrap/doco-cd/compose.yaml doco-cd`**

Expected: service `doco-cd_doco-cd` (or similarly named) running on a manager.

- [ ] **Step 5: Encrypt Arcane secrets; commit; wait for poll**

Expected: Arcane stack appears; `docker secret ls` shows rotated/hash-suffixed secrets; Arcane UI reachable.

- [ ] **Step 6: Document any compose/path fixes discovered back into repo; commit**

```bash
git commit -m "$(cat <<'EOF'
docs: record bootstrap verification notes

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task(s) |
| --- | --- |
| One env per clone; Swarm-only | README + overall layout |
| doco-cd + Arcane platform | Tasks 4–6 |
| Git SoT; Arcane UI only | docs + compose labels/`managed-by` |
| App-centric `apps/`; doco-cd in `bootstrap/` | Tasks 4–6 |
| SOPS + age; Docker secrets runtime; public key in git | Tasks 2, 4, 6 |
| Minimal human bootstrap | `bootstrap/README.md` Task 4 |
| Day-2 add/change/rotate | `docs/day-2-apps.md` Task 3 |
| Self-update + recovery | `.doco-cd.yaml` + bootstrap recovery Task 4–5 |
| Out of scope node IaC | Not planned |
| Remove plaintext Arcane draft | Task 6 |

**Placeholder scan:** No TBD steps; placeholders for age key / GitHub URL are explicit replace-during-bootstrap values.

**Type/name consistency:** Docker secret names `sops_age_key`, `git_access_token`; Arcane file secrets `encryption_key.enc.txt`, `jwt_secret.enc.txt`, `database_url.enc.txt`; labels `cloud.subtract.*`.
