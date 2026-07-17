# Swarm GitOps Template

One clone of this repository = one Docker Swarm environment.

Git is the desired-state source of truth. [doco-cd](https://doco.cd/) polls this repo, decrypts [SOPS](https://getsops.io/) secrets, and deploys Swarm stacks. Runtime secrets live as **Docker secrets**. [Arcane](https://getarcane.app/) is the management UI — not a second source of truth.

## Quick start

1. Follow the operator checklist in **[bootstrap/ansible/README.md](bootstrap/ansible/README.md)**.
2. Install the pinned Ansible dependencies and run `make lint`.
3. Run `make greenfield` to take new Ubuntu 24.04 hosts through hardening, Netbird, Swarm creation, doco-cd deployment, and verification.
4. Add workloads under `apps/<name>/` — see [docs/apps.md](docs/apps.md).

For an existing environment, use `make join` to bootstrap inventory hosts in `new_nodes`, or `make verify` for non-mutating completion checks. The architecture and completion contracts are in [docs/ansible-bootstrap.md](docs/ansible-bootstrap.md).

## Layout

- `bootstrap/ansible/` — inventory, playbooks, roles, and the operator runbook
- `apps/` — doco-cd, Traefik (ingress), Arcane, and all other stacks
- `docs/` — [ansible-bootstrap](docs/ansible-bootstrap.md), [apps](docs/apps.md), [security policy](docs/security-policy.md)
- Spec: `docs/superpowers/specs/2026-07-14-swarm-gitops-template-design.md`

## Validate

```bash
./scripts/validate-layout.sh
```
