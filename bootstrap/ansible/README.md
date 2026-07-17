# Ansible bootstrap

This is the operator runbook for greenfield bootstrap, joining new nodes, and
non-mutating verification. Run all `make` commands from the repository root.

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
8. After greenfield bootstrap, confirm SOPS ciphertext in
   `bootstrap/ansible/secrets/` is committed and all repo-root plaintext has
   been deleted.

Install pinned Galaxy dependencies once:

```sh
ansible-galaxy install -r bootstrap/ansible/requirements.yml
```

Run `make lint` before executing a playbook. Then use:

- `AGE_BACKUP_CONFIRMED=yes make greenfield` for a new environment.
- `make join` after adding new inventory hosts to `new_nodes`.
- `make verify` for completion-contract checks that do not mutate hosts.

## Bootstrap-window cutover

The lockdown plays connect to each `new_nodes` host through its current
`ansible_host`, create the permanent `bootstrap_user_name`, enroll Netbird,
prove OpenSSH and Ansible connectivity at the discovered Netbird address, and
only then enable UFW without a public SSH allowance.

Ansible cannot persist changes to the YAML inventory. Immediately after each
successful host cutover:

1. Copy the discovered Netbird address into that host's `netbird_ip`.
2. Change `ansible_host` to `{{ netbird_ip }}`.
3. Remove the host from `new_nodes`.

Do this before a second run: public TCP/22 is closed after the first successful
cutover.

See [the design document](../../docs/ansible-bootstrap.md) for inventory
semantics, security decisions, failure behavior, and completion contracts.
