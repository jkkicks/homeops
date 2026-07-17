# doco-cd secrets

## External Docker secrets

| Docker secret name | Contents |
| --- | --- |
| `sops_age_key` | Age private key file contents |
| `git_access_token` | Git HTTPS token / PAT for polling |

Ansible creates each secret during greenfield bootstrap and leaves an existing
secret untouched on later runs. The age private key remains only in the Docker
secret and a cold offline backup; it is never committed, including as SOPS
ciphertext. The Git token is retained as SOPS ciphertext under
`bootstrap/ansible/secrets/`.
