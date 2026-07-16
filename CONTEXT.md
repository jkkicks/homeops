# Homeops

One clone of this repository is one Docker Swarm environment. Git is desired state; doco-cd deploys; Ansible (designed, not yet built) bootstraps hosts into that world.

## Language

**Environment**:
One clone/fork of this template repo corresponding to one Swarm and its config. Inventory and secrets are per environment.
_Avoid_: Cluster (when meaning the git repo), deployment, site

**Greenfield bootstrap**:
The Ansible path that takes new Ubuntu hosts from first public SSH through a verified doco-cd on a new Swarm.
_Avoid_: Full install, day-0 / day-1 / day-2, cluster create

**Apps workflow**:
Adding, changing, and rotating application stacks under `apps/` via git and doco-cd after bootstrap.
_Avoid_: Day-2, day2, post-bootstrap ops (vague)

**Join**:
The Ansible path that takes a new Ubuntu host through hardening, Netbird, and Swarm join as manager or worker on an existing Swarm — without redeploying doco-cd.
_Avoid_: Scale-out (vague), add node (when the full path isn't meant)

**Bootstrap window**:
The short period when a new host still accepts Ansible over public SSH before lockdown to Netbird-only SSH.
_Avoid_: Provisioning phase, temporary access

**Host mesh**:
The Netbird network between Ubuntu hosts used for SSH and Swarm control-plane traffic.
_Avoid_: Overlay (Docker's), VPN (generic), container mesh

**Operator machine**:
The laptop or workstation that runs Ansible and holds staged secrets during greenfield bootstrap.
_Avoid_: Bastion, CI runner, control plane (Swarm)

**Init manager**:
The first host listed under inventory group `managers` — the node that runs `docker swarm init` on greenfield. Not a separate inventory group.
_Avoid_: primary manager (ambiguous), leader (Raft leader is runtime-elected)

**New node**:
A host listed in inventory group `new_nodes` — still in the bootstrap window (public SSH / not yet Netbird-locked).
_Avoid_: Fresh VM (when inventory state isn't meant), uninitialized
