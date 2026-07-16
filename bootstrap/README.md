# Bootstrap

One-time human checklist to take a fresh clone of this repo from "Swarm exists" to "doco-cd is polling git and deploying stacks." After this, app changes are a git workflow — see [docs/apps.md](../docs/apps.md).

Planned replacement for the “Swarm already exists” assumption: [docs/ansible-bootstrap.md](../docs/ansible-bootstrap.md) (design; Ansible not implemented yet).

Run all steps below from a machine that has this repo checked out and a Docker CLI pointed at a **Swarm manager** (via Docker context — see Step 1). You do **not** need to SSH into the manager and run Docker there, as long as the context targets a manager.

---

## 1. Point your local Docker CLI at the Swarm

Bootstrap and later `docker` commands (secrets, stack deploy, service ls/logs) talk to the Swarm API. Create a Docker context on your local machine so the default CLI target is a manager — do this before any later step.

SSH is the usual homelab path (Docker uses your existing SSH config/keys):

```bash
# Name and host are examples — use your manager's SSH user@host
docker context create homeops-swarm \
  --description "Homeops Swarm manager" \
  --docker "host=ssh://USER@MANAGER_HOST"

docker context use homeops-swarm
docker context show   # expect: homeops-swarm
```

If you already manage the daemon over TCP + TLS instead of SSH:

```bash
docker context create homeops-swarm \
  --docker "host=tcp://MANAGER_HOST:2376,ca=~/.docker/ca.pem,cert=~/.docker/cert.pem,key=~/.docker/key.pem"
docker context use homeops-swarm
```

To switch back to the local Docker engine later: `docker context use default`.

---

## 2. Confirm Swarm is ready

With the Swarm context selected:

```bash
docker info --format '{{.Swarm.LocalNodeState}} {{.Swarm.ControlAvailable}}'
```

Expected: `active true` — the context's daemon is an active Swarm member with manager control. If you see `inactive` or `false`, fix the context (wrong host / not a manager) or Swarm status before continuing (node provisioning is out of scope for this repo).

---

## 3. Generate the cluster age keypair

`doco-cd` uses an [age](https://github.com/FiloSottile/age) keypair to decrypt SOPS secrets. Generate one **per clone/environment** — never reuse a private key across environments.

```bash
cd /path/to/this/clone

# Generate the private key
age-keygen -o sops_age_key.txt

# Derive the public key from it
age-keygen -y sops_age_key.txt > age.pubkey
cat age.pubkey
```

1. **Back up `sops_age_key.txt` offline immediately** (e.g. a Vaultwarden secure note or equivalent). This is the _only_ recovery path if the Docker secret is ever lost — see [Lost age key](#9-recovery-lost-age-key). Do this before anything else touches the file.
2. Update the two committed files with the real public key:
   - Replace the placeholder line in `age.pubkey` with the contents of `age.pubkey.new`.
   - Replace the placeholder `age:` value in `.sops.yaml` with the same public key.
3. Commit:

```bash
git add age.pubkey .sops.yaml
git commit -m "$(cat <<'EOF'
chore: set real cluster age public key for this environment

EOF
)"
git push
```

Keep `sops_age_key.txt` (the **private** key) out of git — it is already covered by `.gitignore`. Do not delete it yet; you need it for Step 4.

---

## 4. Create the bootstrap Docker secrets

Two Docker secrets let doco-cd decrypt SOPS ciphertext and authenticate to git. Both are created **external** to compose (see `bootstrap/doco-cd/compose.yaml`) so the very first deploy — before doco-cd has ever run — already has what it needs.

Use file redirection, not `echo`/inline args, so secret material never lands in shell history.

```bash
docker secret create \
  --label cloud.subtract.application=doco-cd \
  --label cloud.subtract.environment=production \
  --label cloud.subtract.managed-by=manual \
  --label cloud.subtract.provisioning-source=bootstrap \
  --label cloud.subtract.purpose=sops-age-private-key \
  sops_age_key - < sops_age_key.txt
```

```bash
# Create a Git PAT (or deploy token) scoped to read this repo, then:
# The file must contain ONLY the raw token (e.g. github_pat_… or ghp_…).
# No labels ("github PAT:"), quotes, or trailing newline — those cause
# "Invalid username or token" on poll.
export GIT_TOKEN='YOUR_ACTUAL_TOKEN_HERE'
printf '%s' "$GIT_TOKEN" > git_access_token.txt
docker secret create \
  --label cloud.subtract.application=doco-cd \
  --label cloud.subtract.environment=production \
  --label cloud.subtract.managed-by=manual \
  --label cloud.subtract.provisioning-source=bootstrap \
  --label cloud.subtract.purpose=git-access-token \
  git_access_token - < git_access_token.txt
```

Verify both exist:

```bash
docker secret ls --filter label=cloud.subtract.application=doco-cd
```

Now shred the local plaintext copies — they only need to exist long enough to load into Docker secrets and the offline backup:

```bash
rm -f sops_age_key.txt git_access_token.txt age.pubkey.new
```

(`sops_age_key.txt` should already be safely backed up offline per Step 3 before you shred it here.)

---

## 5. Point `poll-config.yaml` at this clone's remote

Edit `bootstrap/doco-cd/poll-config.yaml`:

```yaml
- url: https://github.com/YOUR-ORG/YOUR-REPO.git
  reference: refs/heads/main
  interval: 60s
```

- `url` — this clone's actual git remote (HTTPS form, since `git_access_token` is an HTTPS PAT).
- `reference` — must match the branch you intend to deploy from (typically `refs/heads/main`).

Commit if you changed it:

```bash
git add bootstrap/doco-cd/poll-config.yaml
git commit -m "$(cat <<'EOF'
chore: point doco-cd poll-config at this clone's remote

EOF
)"
git push
```

---

## 6. Deploy doco-cd

The stack's `configs.file: ./poll-config.yaml` entry is resolved **relative to the compose file's location**, not your shell's cwd. Run `docker stack deploy` from the **repo root** on the machine that has the clone (with the Swarm Docker context still selected), passing the path to the compose file exactly as below — the CLI resolves `./poll-config.yaml` against the directory containing `compose.yaml` (i.e. `bootstrap/doco-cd/`) and sends the content to the Swarm. Use a real path (not piped from stdin):

```bash
cd /path/to/this/clone   # repo root
docker stack deploy -c bootstrap/doco-cd/compose.yaml doco-cd
```

If your Docker version has trouble resolving the relative `configs.file` path from a nested compose file, `cd` into `bootstrap/doco-cd/` first and reference the compose file directly instead:

```bash
cd /path/to/this/clone/bootstrap/doco-cd
docker stack deploy -c compose.yaml doco-cd
```

Either form works as long as `poll-config.yaml` sits next to `compose.yaml` when you run the command — which it does in a normal checkout.

---

## 7. Verify

```bash
docker service ls
```

Expected: a service named `doco-cd_doco-cd` (or similar), `1/1` replicas, running on a manager.

```bash
docker service logs -f doco-cd_doco-cd
```

Expected: startup logs showing the poll config loaded, followed by a successful poll/clone of the repo within `interval` (60s). No repeated auth or decrypt errors.

Once `apps/` contains at least one app with real (encrypted) secrets, confirm doco-cd deploys it after a poll cycle:

```bash
docker stack ls
docker service ls
```

---

## 8. Recovery: redeploy doco-cd manually

doco-cd may self-update itself from `bootstrap/doco-cd` (see `.doco-cd.yaml`). If a bad commit or self-update ever breaks doco-cd (crash loop, stuck deploy, wrong image tag, etc.), redeploy it by hand with the Swarm Docker context selected — the same command as first deploy:

```bash
cd /path/to/this/clone
git pull   # make sure you're deploying from a known-good commit
docker stack deploy -c bootstrap/doco-cd/compose.yaml doco-cd
```

`docker stack deploy` is idempotent and safe to re-run. If the service is wedged rather than just outdated, remove and redeploy:

```bash
docker stack rm doco-cd
# wait for the service/network/config to fully tear down
docker stack deploy -c bootstrap/doco-cd/compose.yaml doco-cd
```

Removing the stack does **not** remove the `sops_age_key` / `git_access_token` Docker secrets (they are external) or your git history — recovery only needs the compose file and those two secrets to already exist.

---

## 9. Recovery: lost age key

Swarm secrets are **immutable** — you cannot update `sops_age_key` in place. If the Docker secret is deleted, corrupted, or the manager is rebuilt:

1. Restore the private key from your **offline backup** (from Step 3) to a local file, e.g. `sops_age_key.txt`.
2. Confirm it matches the committed public key:

   ```bash
   age-keygen -y sops_age_key.txt
   # compare output to age.pubkey — must match exactly
   ```

3. With the Swarm Docker context selected, remove the old secret (only once nothing is using it — stop/remove the doco-cd stack first) and recreate it under the **same name** so `bootstrap/doco-cd/compose.yaml` needs no changes:

   ```bash
   docker stack rm doco-cd
   docker secret rm sops_age_key
   docker secret create \
     --label cloud.subtract.application=doco-cd \
     --label cloud.subtract.environment=production \
     --label cloud.subtract.managed-by=manual \
     --label cloud.subtract.provisioning-source=bootstrap \
     --label cloud.subtract.purpose=sops-age-private-key \
     sops_age_key - < sops_age_key.txt
   docker stack deploy -c bootstrap/doco-cd/compose.yaml doco-cd
   ```

4. Shred the local plaintext copy again once the secret is recreated: `shred -u sops_age_key.txt`.
5. Verify decrypt works: check `docker service logs -f doco-cd_doco-cd` for a clean poll/decrypt/deploy cycle on the next interval.

**If the private key was compromised** (not just lost) rather than merely lost, treat it as a rotation, not a restore:

1. Generate a **new** age keypair (Step 3), update `age.pubkey` / `.sops.yaml`, commit and push.
2. Re-encrypt every SOPS file in the repo (`apps/**/secrets/*.enc.*`) with the new public key.
3. Recreate the `sops_age_key` Docker secret with the **new** private key using the same procedure as above.
4. Redeploy doco-cd, then confirm every app's secrets decrypt and Docker secrets rotate cleanly.

---

## Reference

- Docker secrets created here: `sops_age_key`, `git_access_token` (both `external: true` in `bootstrap/doco-cd/compose.yaml`).
- Config: `bootstrap/doco-cd/poll-config.yaml` (committed, mounted as a Swarm config, drives self-update since it lives in the repo).
- Full secret inventory for this stack: [bootstrap/doco-cd/secrets/README.md](doco-cd/secrets/README.md).
- Overall security model: [docs/security-policy.md](../docs/security-policy.md).
