# Design deliverable shape

Type: grilling
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

What artifact(s) count as “the design is done” for this map — path(s), structure (single design doc vs design + ADR(s)), and how that artifact should relate to today’s `bootstrap/README.md` (replace, thin, or pointer) without implementing Ansible yet?

## Answer

**Done artifact:** `docs/ansible-bootstrap.md` — the full Ansible bootstrap design (greenfield through verified doco-cd, join mode, inventory/secrets, hardening/Netbird/Swarm boundaries). Research stays in `docs/research/`; ADRs only if a later decision truly needs one. This map does not implement Ansible.

**Docs / layout the design must prescribe (implement after design, not invent ad hoc):**

- Operator docs live under `docs/`, organized plainly (no day-N jargon).
- Bootstrap docs cover the full Ansible path **including deploying and verifying doco-cd**.
- doco-cd moves from `bootstrap/doco-cd` → `apps/doco-cd`; `bootstrap/README.md` goes away once content lives in `docs/`.
- Root `README.md` always reflects the **current** operator entrypoint.
- Rename the apps guide: `docs/day-2-apps.md` → `docs/apps.md` (“Apps”). Ban day-0 / day-1 / day-2 wording repo-wide in living docs; describe phases by name (greenfield bootstrap, join, apps workflow). Historical `docs/superpowers/` plans/specs need not be rewritten.
