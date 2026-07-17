# Bootstrap

Ansible is the live bootstrap entrypoint:

- Follow the [operator runbook](ansible/README.md).
- Use `make greenfield`, `make join`, and `make verify` from the repository root.
- See the [Ansible bootstrap design](../docs/ansible-bootstrap.md) for architecture and completion contracts.

After bootstrap, manage application stacks through git under `apps/`; see the
[apps workflow](../docs/apps.md). The doco-cd stack and recovery notes live at
[`apps/doco-cd/`](../apps/doco-cd/).
