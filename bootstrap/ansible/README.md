# Ansible bootstrap

This is the Ansible skeleton for greenfield bootstrap, join, and verification.
Roles are completed by the remaining implementation tasks. Until that work is
finished, follow the live human procedure in [`../README.md`](../README.md).

## Operator machine checklist

Before `make greenfield` or `make join`:

1. Clone this environment repo and confirm the operator machine can reach new
   hosts over public SSH using the inventoried key or password.
2. Enroll the operator peer in Netbird Cloud and the environment group (for
   example, `{env}-operators`) so mesh SSH continues after cutover.
3. Install Ansible, `ansible-lint`, `age`, and `sops`. The Docker CLI is
   optional for checking a manager over SSH after the Swarm exists.
4. Fill `bootstrap/ansible/inventory/hosts.yml`, including `managers`,
   `workers`, `new_nodes`, `public_ip`, `hostname`, and the SSH shape.
5. Put only public keys to install under the root `ssh-keys/` directory.
6. Copy the required root `*.example` files, fill the staged bootstrap-window
   secrets, and run `make age-key`. Make a cold offline backup of the age
   private key before greenfield bootstrap.
7. In Netbird, create a setup key with automatic environment-group assignment.
   Configure full access in that group and TCP 80/443 from other Netbird peers.
8. After greenfield bootstrap, confirm SOPS ciphertext in `secrets/` is
   committed and all repo-root plaintext has been deleted.

Install pinned Galaxy dependencies once:

```sh
ansible-galaxy install -r bootstrap/ansible/requirements.yml
```

Run `make lint` before executing a playbook.
