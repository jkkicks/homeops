# bootstrap/doco-cd secrets

## External (human bootstrap — Docker secrets)

| Docker secret name   | Contents                          |
| -------------------- | --------------------------------- |
| `sops_age_key`       | Age private key file contents     |
| `git_access_token`   | Git HTTPS token / PAT for polling |

These stay external so the first deploy and SOPS decrypt never require ciphertext the agent cannot yet read.

## Optional later

Additional encrypted files for doco-cd may be added here once SOPS decrypt is proven; prefer keeping chicken-and-egg credentials external.
