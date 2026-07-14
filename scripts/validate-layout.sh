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
