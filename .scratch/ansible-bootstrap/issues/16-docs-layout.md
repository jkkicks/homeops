# Docs directory layout

Type: grilling
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

Beyond `docs/ansible-bootstrap.md`, `docs/apps.md`, `docs/security-policy.md`, and `docs/research/`, what `docs/` layout should the design prescribe for v1?

## Answer

Flat `docs/` for v1:

- `docs/ansible-bootstrap.md` — Ansible bootstrap design / operator bootstrap
- `docs/apps.md` — apps workflow
- `docs/security-policy.md`
- `docs/research/` — research notes
- `docs/superpowers/` — archived history (unchanged)

Cross-link with relative markdown links between living docs. Nest only when a second bootstrap/ops doc forces it. Root `README.md` links current entrypoints.
