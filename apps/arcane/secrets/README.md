# Arcane secrets

Arcane's `compose.yaml` reads three file-backed secrets via `*_FILE` env vars:

| Secret file (in this dir)      | Docker secret name        | Consumed as                   |
| ------------------------------- | -------------------------- | ------------------------------ |
| `encryption_key.enc.txt`        | `arcane_encryption_key`    | `ENCRYPTION_KEY__FILE`         |
| `jwt_secret.enc.txt`            | `arcane_jwt_secret`        | `JWT_SECRET__FILE`             |
| `database_url.enc.txt`          | `arcane_database_url`      | `DATABASE_URL__FILE`           |

Only SOPS ciphertext is ever committed here. doco-cd decrypts these files in place (using the cluster's age private key) before creating/rotating the corresponding Docker secrets.

## ⚠️ Rotate old secrets

`apps/arcane.yaml` (a pre-migration local draft, never intended to be committed) contained **plaintext** `ENCRYPTION_KEY`, `JWT_SECRET`, and `POSTGRES_PASSWORD` values. Treat every value that ever appeared in that file — or in any other local `apps/arcane*.yaml` draft — as **compromised**:

- Generate brand-new values for `arcane_encryption_key` and `arcane_jwt_secret` (do **not** reuse the ones from the old draft).
- Rotate the Neon (or other) database password/connection string backing `arcane_database_url`.
- Never copy values from old drafts into the encrypted files below.

## Generate and encrypt (after real `age.pubkey` is set)

This repo ships with a **placeholder** age public key in `age.pubkey` / `.sops.yaml`. Encryption will fail until bootstrap replaces it with the real cluster key (see `bootstrap/README.md`). Once that's done:

```bash
# After bootstrap updated age.pubkey / .sops.yaml:
umask 077
openssl rand -hex 32 > /tmp/arcane_encryption_key.plain
openssl rand -hex 32 > /tmp/arcane_jwt_secret.plain
# database_url: paste the real (freshly rotated) connection string
printf '%s' "$DATABASE_URL" > /tmp/arcane_database_url.plain

sops encrypt --age "$(cat age.pubkey | grep -v '^#' | head -1)" \
  /tmp/arcane_encryption_key.plain > apps/arcane/secrets/encryption_key.enc.txt
sops encrypt --age "$(cat age.pubkey | grep -v '^#' | head -1)" \
  /tmp/arcane_jwt_secret.plain > apps/arcane/secrets/jwt_secret.enc.txt
sops encrypt --age "$(cat age.pubkey | grep -v '^#' | head -1)" \
  /tmp/arcane_database_url.plain > apps/arcane/secrets/database_url.enc.txt

shred -u /tmp/arcane_*.plain
```

Commit only the resulting `*.enc.txt` files. Remove `.gitkeep` once at least one encrypted file exists (optional — its presence is harmless).

## Rotate later

```bash
sops edit apps/arcane/secrets/<file>.enc.txt
git add apps/arcane/secrets/<file>.enc.txt
git commit -m "chore: rotate arcane secret"
git push
```

doco-cd re-decrypts on the next poll, rotates the Docker secret (content-hash suffixed), and redeploys Arcane against the new value.
