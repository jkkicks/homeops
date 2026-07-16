# Default Swarm manager quorum

Type: grilling
Status: resolved

Part of: [.scratch/ansible-bootstrap/map.md](../map.md)

## Question

For greenfield in this template, what default manager topology should the design prescribe (single manager vs three for quorum), and how should the inventory/docs express that without blocking one-node labs?

## Answer

**No prescribed manager count.** Inventory under `managers` is the only topology input — 1, 3, 5, … are all valid. Ansible does not enforce a minimum or maximum.

Docs may include a one-liner that Swarm Raft wants an **odd** manager count for quorum; operators are assumed to know HA tradeoffs. Example inventory can show a single-manager lab without implying that’s the only shape.
