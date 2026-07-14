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
