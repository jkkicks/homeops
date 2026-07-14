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
