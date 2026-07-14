# bootstrap/doco-cd secrets

## External (human bootstrap — Docker secrets)

| Docker secret name   | Contents                          |
| -------------------- | --------------------------------- |
| `sops_age_key`       | Age private key file contents     |
| `git_access_token`   | Git HTTPS token / PAT for polling |

These stay external so the first deploy and SOPS decrypt never require ciphertext the agent cannot yet read.

**Create/recreate them via [bootstrap/README.md](../../README.md) Step 4** (not by editing this file). For `git_access_token`, the Docker secret must be the raw PAT only (`github_pat_…` / `ghp_…`) — no `github PAT:` label, quotes, or extra whitespace. Use `printf '%s' "$GIT_TOKEN" > git_access_token.txt` as shown there; a malformed secret surfaces as `Invalid username or token` on poll.

## Optional later

Additional encrypted files for doco-cd may be added here once SOPS decrypt is proven; prefer keeping chicken-and-egg credentials external.
