# Ansible bootstrap secrets

This directory contains committed SOPS ciphertext only, such as
`git_access_token.sops.yml`. Never place plaintext secrets here.

Files matching `*.sops.yml` and `*.enc.*` are intentionally tracked by Git.
