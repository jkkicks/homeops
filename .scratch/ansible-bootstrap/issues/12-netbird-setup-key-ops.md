# Netbird setup key operations

Type: grilling
Status: resolved
Blocked by: 01

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

How should operators create, scope (one-off vs reusable, groups, expiry), store (`netbird_setup_key.txt`), and rotate Netbird setup keys for greenfield and join — as a design/runbook decision, not dashboard how-to duplication?

## Answer

### Create / scope

- Create under Netbird Cloud **Settings → Setup Keys** (not the 24h Add-Peer shortcut) so expiry, usage limit, and auto-groups are controllable.
- Prefer **reusable + tight usage limit** sized to the batch, short expiry; one-off keys OK for a single host.
- Auto-assign peers into the group used for SSH/Swarm ACLs (ACL detail is a separate fog item).

### Store / consume

- Operator copies `netbird_setup_key.txt.example` → `netbird_setup_key.txt` (gitignored), fills the key.
- Ansible reads the file and runs `netbird up --setup-key …`. No Netbird API key lifecycle in v1.
- Scrub after the run like other staged secrets.

### Rotate

- Revoke/expire in the dashboard when the run finishes or a key may have leaked (blocks new enrollments only; existing peers stay connected).
- Next greenfield/join uses a fresh `netbird_setup_key.txt`.

### Example files (applies to all staged operator secrets)

Ship committed `*.example` (or `*.example.txt`) siblings for every file the operator must create by hand — e.g. `netbird_setup_key.txt.example`, `git_access_token.txt.example`, bootstrap SSH secret examples — so the workflow is: duplicate → rename → fill. `sops_age_key.txt` remains `make age-key` generated (example optional / N/A).
