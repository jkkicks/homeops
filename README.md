# Swarm GitOps Template

One clone of this repository = one Docker Swarm environment.

Git is the desired-state source of truth. [doco-cd](https://doco.cd/) polls this repo, decrypts [SOPS](https://getsops.io/) secrets, and deploys Swarm stacks. Runtime secrets live as **Docker secrets**. [Arcane](https://getarcane.app/) is the management UI — not a second source of truth.

## Quick start

1. Swarm already initialized (node IaC is out of scope for the current checklist).
2. Follow **[bootstrap/README.md](bootstrap/README.md)** — local Docker context on a Swarm manager, age key, git credentials, first doco-cd deploy.
3. Add workloads under `apps/<name>/` — see [docs/apps.md](docs/apps.md).

**Planned:** bare-metal → Swarm bootstrap via Ansible — see [docs/ansible-bootstrap.md](docs/ansible-bootstrap.md) (design only; not implemented yet). Operator machine prerequisites are in that doc (§8).

## Layout

- `bootstrap/` — human one-time steps + doco-cd today; Ansible will live under `bootstrap/ansible/`
- `apps/` — Traefik (ingress), Arcane, and all other stacks (doco-cd moves here with Ansible)
- `docs/` — [ansible-bootstrap](docs/ansible-bootstrap.md), [apps](docs/apps.md), [security policy](docs/security-policy.md)
- Spec: `docs/superpowers/specs/2026-07-14-swarm-gitops-template-design.md`

## Validate

```bash
./scripts/validate-layout.sh
```
