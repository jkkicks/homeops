# Docker Swarm control plane over Netbird

**Question:** What do Docker’s primary docs say about initializing and joining Swarm with `--advertise-addr` / `--data-path-addr` (or equivalents) on a WireGuard-style overlay NIC such as Netbird: required flags, manager vs worker behavior, multi-homed host pitfalls, and what traffic stays on the Docker overlay vs the host mesh?

**Context (already decided for this repo):** Netbird is the host mesh; Docker overlay networks remain for container traffic. Greenfield Ubuntu 24.04 init + join paths.

**Sources:** Docker Engine docs on docs.docker.com (primary). Netbird first-party docs only for default interface name.

---

## Summary

On multi-homed hosts (typical once Netbird’s `wt0` exists alongside a public/LAN NIC), Docker **requires** an explicit `--advertise-addr` so peers learn the correct address for Swarm API / inter-manager traffic and for overlay peer reachability. `--data-path-addr` is optional; if omitted it defaults to the advertise address, so both control and VXLAN underlay targeting use the same IP. Pointing those flags at the Netbird address (or interface) puts Swarm’s host-to-host packets on the mesh underlay; container-to-container addressing still uses Docker’s overlay (VXLAN) networks on top of that underlay. Docker does not document Netbird specifically.

---

## Required and related flags

### `--advertise-addr`

Format: `<ip|interface>[:port]`. Port optional; default **2377**.

Docker documents that this is the address **advertised to other swarm members for API access and overlay networking**. If unspecified, Docker uses the host’s sole IP with the listen port. **If the system has multiple IP addresses, `--advertise-addr` must be specified** so the correct address is chosen for inter-manager communication and overlay networking. An interface name is allowed (e.g. `eth0:2377`).

Sources:

- [docker swarm init — `--advertise-addr`](https://docs.docker.com/reference/cli/docker/swarm/init/#advertise-addr)
- [docker swarm join — `--advertise-addr`](https://docs.docker.com/reference/cli/docker/swarm/join/#advertise-addr)
- [Run Docker Engine in swarm mode — Configure the advertise address](https://docs.docker.com/engine/swarm/swarm-mode/#configure-the-advertise-address)

### Reachability vs local view (multi-homed / cloud pitfall)

You must also set `--advertise-addr` when **the address other nodes use to reach the manager is not the address the manager sees as its own** (e.g. internal vs external addresses across regions). Other nodes must be able to reach the manager on its advertise address.

Source: [Configure the advertise address](https://docs.docker.com/engine/swarm/swarm-mode/#configure-the-advertise-address)

Implication for Netbird: advertise the **Netbird mesh IP** (or the Netbird interface) that peers use to reach each other, not a public cloud IP that is not the path you intend for Swarm.

### `--listen-addr`

Format: `<ip|interface>[:port]`. Default **`0.0.0.0:2377`**.

This is where the node **listens for inbound swarm manager traffic**. It is distinct from the advertised address. On join, Docker notes this flag is generally unnecessary for existing swarms; it matters when the node is (or becomes) a manager listening for manager traffic.

Sources:

- [docker swarm init — `--listen-addr`](https://docs.docker.com/reference/cli/docker/swarm/init/#listen-addr)
- [docker swarm join — `--listen-addr`](https://docs.docker.com/reference/cli/docker/swarm/join/#listen-addr)

### `--data-path-addr`

Format: `<ip|interface>` (API 1.31+).

This is the address that **global-scope network drivers publish so other nodes can reach containers on this node**. It lets you separate **container data traffic** from **cluster management traffic**. If unspecified, Docker uses the advertise address’s IP or interface.

Important binding caveat (init docs): setting `--data-path-addr` **does not restrict** which interfaces or source IPs the VXLAN socket binds to; like advertise-addr, it tells other members **which address to use**. Restrict VXLAN access with firewall rules.

Sources:

- [docker swarm init — `--data-path-addr`](https://docs.docker.com/reference/cli/docker/swarm/init/#data-path-addr)
- [docker swarm join — `--data-path-addr`](https://docs.docker.com/reference/cli/docker/swarm/join/#data-path-addr)
- [Manage swarm service networks — separate control and data interfaces](https://docs.docker.com/engine/swarm/networking/#use-a-separate-interface-for-control-and-data-traffic)

### `--data-path-port`

UDP port for data-path traffic (1024–49151). Default **4789** if unset or `0`. **Only configurable at `swarm init`**; applies to all nodes that later join. Verify with `docker info` → `Data Path Port`.

Source: [docker swarm init — `--data-path-port`](https://docs.docker.com/reference/cli/docker/swarm/init/#data-path-port)

Doc inconsistency: the [overlay driver requirements table](https://docs.docker.com/engine/network/drivers/overlay/#requirements) says `4789/udp` is configurable with `docker swarm init --data-path-addr`. That conflicts with the init reference, which configures the **port** via `--data-path-port` and the **address** via `--data-path-addr`. Prefer the CLI reference.

---

## Manager vs worker behavior

| Concern | What Docker docs say |
| --- | --- |
| Role | Join token selects manager vs worker (`docker swarm join --token …`). |
| Same address flags | Both `swarm init` and `swarm join` accept `--advertise-addr` and `--data-path-addr`. |
| Multi-IP rule | Join reference repeats: with multiple IPs, `--advertise-addr` **must** be specified for correct inter-manager and overlay networking. |
| “Generally not necessary” | Join docs also say `--advertise-addr` is generally not necessary when joining, except e.g. joining through a load balancer so the node advertises its own IP—not the LB’s. Treat that as the single-homed / simple case; multi-homed still requires an explicit advertise address. |
| Manager listen | `--listen-addr` on join applies if the node is a manager (inbound manager traffic). |
| Manager stability | Join docs: managers should be stable hosts with **static IP addresses**; keep manager count odd (recommend 3 or 5) for Raft quorum. |
| Workers | Overlay walkthroughs commonly pass `--advertise-addr` on workers as well as the manager. |

Sources:

- [docker swarm join](https://docs.docker.com/reference/cli/docker/swarm/join/)
- [Join nodes to a swarm](https://docs.docker.com/engine/swarm/join-nodes/)
- [Overlay network driver — multi-node setup](https://docs.docker.com/engine/network/drivers/overlay/#create-the-swarm)

Greenfield pattern consistent with docs:

```bash
# First manager (Netbird IP or interface; example uses interface name)
docker swarm init --advertise-addr wt0
# optional explicit data path (defaults to advertise-addr if omitted):
# docker swarm init --advertise-addr wt0 --data-path-addr wt0

# Join (token + manager's advertised HOST:PORT from join-token output)
docker swarm join --token <TOKEN> --advertise-addr wt0 <MANAGER-NETBIRD-IP>:2377
```

(Interface name `wt0` is Netbird’s default; an explicit Netbird IP is equally valid per Docker’s `<ip|interface>` format.)

---

## Multi-homed host pitfalls

1. **Multiple IPs ⇒ required `--advertise-addr`.** A host with a public/LAN address plus a Netbird address is multi-homed; omitting the flag risks advertising the wrong NIC.
2. **Advertise the path peers actually use.** If you advertise a non-mesh address while only Netbird connectivity is allowed between nodes, join and overlay peer setup fail reachability checks described in swarm-mode docs.
3. **Join target must be the manager advertise address:port** printed by `swarm init` / `join-token` (typically that IP:2377).
4. **`--data-path-addr` is publish-only for peers**, not a bind lock; firewall still needed if you must confine VXLAN.
5. **Optional split planes:** `--advertise-addr` for join/leave/manage traffic; `--data-path-addr` for traffic among service containers. With multiple interfaces, advertise must be set explicitly; data-path defaults to advertise if omitted.
6. **Default overlay address pool** `10.0.0.0/8` can conflict with existing space; override only at init via `--default-addr-pool` / `--default-addr-pool-mask-length`.

Sources: init/join advertise and data-path sections above; [swarm-mode default address pools](https://docs.docker.com/engine/swarm/swarm-mode/#configuring-default-address-pools); [separate control and data traffic](https://docs.docker.com/engine/swarm/networking/#use-a-separate-interface-for-control-and-data-traffic).

---

## What traffic is Docker overlay vs host mesh

### Two Docker traffic kinds

Docker swarm generates:

1. **Control and management plane** — join/leave/manage the swarm; **always encrypted**.
2. **Application data plane** — container traffic and external client traffic; **not encrypted by default** on overlay networks unless created with `--opt encrypted` (IPsec at VXLAN).

Source: [Manage swarm service networks — Swarm and types of traffic](https://docs.docker.com/engine/swarm/networking/#swarm-and-types-of-traffic); [encryption](https://docs.docker.com/engine/swarm/networking/#encryption).

### Ports between Docker hosts

| Port | Role |
| --- | --- |
| `2377/tcp` | Default Swarm control plane (listen/advertise; configurable via listen-addr) |
| `4789/udp` | Overlay (incl. ingress) data path (port via `--data-path-port` at init) |
| `7946/tcp` and `7946/udp` | Container network discovery / communication among nodes (not configurable) |

Sources: [Firewall considerations](https://docs.docker.com/engine/swarm/networking/#firewall-considerations); [Overlay requirements](https://docs.docker.com/engine/network/drivers/overlay/#requirements).

### Overlay vs underlay (host mesh)

- Docker’s **overlay driver** creates a distributed network that **sits on top of (overlays) the host-specific networks**; Docker routes packets to the correct daemon host and container. Swarm mode is required for multi-host overlay.
- Source: [Overlay network driver](https://docs.docker.com/engine/network/drivers/overlay/).
- With `--advertise-addr` / `--data-path-addr` aimed at Netbird, **Swarm control-plane TCP and VXLAN/gossip underlay packets** are sent toward those mesh IPs—so they ride the **host mesh (Netbird/WireGuard)** as the underlay.
- **Container east-west addressing** remains on **Docker overlay networks** (`ingress`, user overlays): VXLAN encapsulation between daemons, then delivery into containers. That is separate from Netbird’s peer VPN; Netbird does not replace Docker overlay for service networking.
- Separating `--advertise-addr` and `--data-path-addr` only chooses **which host interface/IP** carries control vs published data-path underlay; both can still be Netbird, or one mesh and one other NIC, per the networking guide’s dual-interface examples.

### Netbird interface naming (non-Swarm fact)

Netbird’s agent default WireGuard interface name is **`wt0`** (`--interface-name`, default `"wt0"`; config key `WgIface`).

Sources: [NetBird CLI](https://docs.netbird.io/get-started/cli); [Bootstrap peers via config file](https://docs.netbird.io/manage/peers/bootstrap-via-config-file).

---

## Practical takeaway for this repo

For greenfield Ubuntu 24.04 nodes that are already on Netbird before Swarm:

1. Treat nodes as multi-homed → always pass `--advertise-addr` (Netbird IP or `wt0`) on **init and join**.
2. Leave `--data-path-addr` unset to inherit advertise (both planes over Netbird), unless you intentionally split data onto another NIC.
3. Use the manager’s Netbird address as the `HOST:PORT` in `docker swarm join`.
4. Ensure Swarm ports (`2377/tcp`, `4789/udp`, `7946/tcp+udp`) are allowed **between peers on the mesh path** you advertised.
5. Keep Docker overlay networks for container traffic; Netbird remains the host underlay/mesh only.

---

## Source index

| Source | URL |
| --- | --- |
| `docker swarm init` CLI | https://docs.docker.com/reference/cli/docker/swarm/init/ |
| `docker swarm join` CLI | https://docs.docker.com/reference/cli/docker/swarm/join/ |
| Run Engine in swarm mode | https://docs.docker.com/engine/swarm/swarm-mode/ |
| Join nodes to a swarm | https://docs.docker.com/engine/swarm/join-nodes/ |
| Manage swarm service networks | https://docs.docker.com/engine/swarm/networking/ |
| Overlay network driver | https://docs.docker.com/engine/network/drivers/overlay/ |
| NetBird CLI (iface name only) | https://docs.netbird.io/get-started/cli |
| NetBird bootstrap config (`WgIface`) | https://docs.netbird.io/manage/peers/bootstrap-via-config-file |
