# Swarm GitOps Template

One clone of this repository = one Docker Swarm environment.

Git is the desired-state source of truth. [doco-cd](https://doco.cd/) polls this repo, decrypts [SOPS](https://getsops.io/) secrets, and deploys Swarm stacks. Runtime secrets live as **Docker secrets**. [Arcane](https://getarcane.app/) is the management UI — not a second source of truth.

## Quick start

1. Swarm already initialized (node IaC is out of scope here).
2. Follow **[bootstrap/README.md](bootstrap/README.md)** — start with a local Docker context pointed at a Swarm manager, then age key, git credentials, and first doco-cd deploy.
3. Add workloads under `apps/<name>/` — see [docs/day-2-apps.md](docs/day-2-apps.md).

## Layout

- `bootstrap/` — human one-time steps + doco-cd
- `apps/` — Arcane and all other stacks
- `docs/` — security policy and day-2 guides
- Spec: `docs/superpowers/specs/2026-07-14-swarm-gitops-template-design.md`

## Validate

```bash
./scripts/validate-layout.sh
```
