# Security policy

Related: [Ansible bootstrap design](ansible-bootstrap.md) · [Apps](apps.md)

## Runtime

- Docker secrets are the runtime system of truth for secret values.
- Services consume secrets via Swarm secret mounts / `*_FILE` paths under `/run/secrets/`.

## Git

- Only SOPS ciphertext is committed for secret values.
- Age **public** key and `.sops.yaml` are committed so operators can encrypt.
- Age **private** key is never committed. It exists as a Docker secret on managers and as an offline backup (e.g. Vaultwarden) for recovery only.

## Bootstrap chicken-and-egg

Human creates (today’s checklist) or Ansible greenfield will create:

1. Age private key → Docker secret (e.g. `sops_age_key`)
2. Git credential → Docker secret (e.g. `git_access_token`) for first doco-cd deploy
3. Deploys doco-cd (`bootstrap/doco-cd` today; `apps/doco-cd` after Ansible lands)

After that, app secrets are managed from encrypted files in git via doco-cd.

Long-lived **operator-side** Ansible secrets (when Ansible exists) are SOPS ciphertext under **`bootstrap/ansible/secrets/`**, **committed** like app secrets. Bootstrap-window plaintext at repo root is gitignored; after greenfield, required secrets are SOPS’d into that directory and root plaintext is deleted. The age **private** key is never committed (cold backup + Docker secret only). See [ansible-bootstrap.md](ansible-bootstrap.md).

## Forbidden

- Plaintext secrets in git
- Treating Arcane as durable desired state outside git
- Long-term reliance on plaintext bind-mounted secret files when Docker secrets can be used
