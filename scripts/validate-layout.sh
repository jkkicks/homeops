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
need "apps/arcane/secrets/README.md"
if [[ ! -f apps/arcane/secrets/encryption_key.enc.txt ]]; then
  need "apps/arcane/secrets/.gitkeep"
  ok "arcane secrets pending encryption (.gitkeep present)"
else
  need "apps/arcane/secrets/encryption_key.enc.txt"
  need "apps/arcane/secrets/jwt_secret.enc.txt"
  need "apps/arcane/secrets/database_url.enc.txt"
fi
need "docs/security-policy.md"
need "docs/day-2-apps.md"

# Forbid known plaintext secret dumps
if [[ -f "apps/arcane.yaml" ]]; then
  fail "apps/arcane.yaml must be removed (contained plaintext secrets)"
fi

# Smell test: no ENC[-looking] plaintext KEY= with common secret names in tracked compose without .enc
tracked_env_files="$(git ls-files '*.yaml' '*.yml' '*.env' 2>/dev/null || true)"
if [[ -n "$tracked_env_files" ]]; then
  if printf '%s\n' $tracked_env_files | xargs grep -nE '^(JWT_SECRET|ENCRYPTION_KEY|POSTGRES_PASSWORD|DATABASE_URL)=' 2>/dev/null | grep -v '\.enc\.' ; then
    fail "possible plaintext secret assignment in tracked files"
  fi
fi
ok "no obvious plaintext secret assignments in tracked env-style files"

# Private age key must not be committed
if git ls-files | grep -E '(^|.*/)(sops_age_key\.txt|age-key\.txt|\.age-key)$' ; then
  fail "age private key file appears tracked by git"
else
  ok "no tracked age private key filenames"
fi

echo "All layout checks passed."
