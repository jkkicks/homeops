# Swarm GitOps Template — Vision Spec

**Date:** 2026-07-14  
**Status:** Draft for review  
**Scope:** End-state product vision (what it looks like and how it feels to operate). Not an implementation plan or codebase architecture deep-dive.

## 1. Purpose

This repository is a **cloneable GitOps / SwarmOps starter** for a single Docker Swarm environment.

## 2. End-state product shape

### 2.1 What “done” looks like

A fresh clone of this template, after a short secure bootstrap on an already-initialized Swarm, yields:

1. **doco-cd** running as the GitOps agent (polls this repo, applies desired state).
2. **Arcane** running as the Swarm/Compose management UI (observe and operate; not the source of truth).
3. A clear place to add more apps under `apps/`, each with stack definitions and SOPS-encrypted secrets.
4. **All runtime secrets** present as **Docker secrets**; no reliance on plaintext env in git or long-lived secret files on disk as the system of record.

### 2.2 Source of truth

| Concern                        | Source of truth                                                       |
| ------------------------------ | --------------------------------------------------------------------- |
| Desired stacks / compose       | Git                                                                   |
| Secret _values_ at rest in git | SOPS ciphertext only                                                  |
| Secret _values_ at runtime     | Docker secrets                                                        |
| Cluster decrypt material       | Age private key as a Docker secret (plus offline backup for recovery) |
| Ad-hoc visibility / debug      | Arcane + Docker CLI                                                   |

Git is the **only** desired-state authoring path. Durable changes are commits. Arcane does not permanently define stacks outside git.

### 2.3 Platform vs workloads

**Initial platform (extensible):**

- **doco-cd** — continuous delivery / reconciliation for Swarm stacks and secret materialization.
- **Arcane** — management UI.

The platform set is expected to grow later (e.g. reverse proxy). The vision assumes growth without changing the core loop: commit → poll → deploy → Docker secrets.

**Workloads:** everything under `apps/` (including Arcane).

## 3. Repository structure (end-state layout)

App-centric layout. Bootstrap is the only human touchpoint folder; everything else is applied by the platform from git.

```text
<repo>/                         # one clone = one Swarm environment
├── bootstrap/
│   ├── README.md               # human one-time checklist
│   └── doco-cd/                # CD agent definition (stays here)
│       ├── compose.yaml
│       └── secrets/            # SOPS-encrypted inputs for doco-cd
├── apps/
│   ├── arcane/
│   │   ├── compose.yaml
│   │   └── secrets/
│   └── <app>/
│       ├── compose.yaml
│       └── secrets/
├── docs/                       # vision, security policy, runbooks
└── README.md
```

### 3.1 Conventions

- **One directory per app** — stack definition and encrypted secrets travel together.
- **No plaintext secrets in git** — only SOPS ciphertext.
- **doco-cd lives under `bootstrap/`** — not under `apps/`. It may **self-update** from that path if doing so is not a material security, performance, or recoverability risk. If self-update is unsafe or fails, the bootstrap runbook must still allow a human to redeploy doco-cd manually.
- **Arcane is a normal app** under `apps/arcane/` so it is fully managed from git after bootstrap.
- **Naming / labels** — runtime resources should carry a stable ownership contract (e.g. labels in the `cloud.subtract.*` style already used in drafts). Exact schema is an implementation detail; the vision requires consistent, queryable ownership metadata.
- **Docker secret naming** — predictable and app-scoped; rotation may use content hashing / suffixes as provided by doco-cd’s Swarm secret handling.

## 4. Secrets and security policy

### 4.1 Principles

1. **Docker secrets are the runtime system of truth** for secret material consumed by services.
2. **SOPS + age** protect secrets in git. Humans encrypt with the **cluster age public key**.
3. **Cluster-only decrypt** for day-to-day operations: the age **private** key exists on Swarm managers as a Docker secret used by doco-cd. Developers do not need the private key for normal commits.
4. **Public key (and SOPS config) live in git** — e.g. `.sops.yaml` and/or a committed age public key — so anyone with repo access can encrypt new secrets without holding decrypt material.
5. **Offline backup** of the age private key is required (e.g. Vaultwarden or another highly secure store). That backup is for **recovery only**, not a second runtime source of truth and not used by the platform in steady state.
6. **Minimize human bootstrap** without weakening the above. Prefer platform automation for all secrets after the chicken-and-egg decrypt key and git access exist.

### 4.2 What is never allowed

- Committing plaintext secrets, tokens, or private keys to git.
- Treating Arcane (or any UI) as a durable secret or stack store outside git.
- Relying on bind-mounted plaintext secret files as the long-term secret store when Docker secrets can be used.

### 4.3 Optional future

Third-party secret managers (AWS Secrets Manager, Vaultwarden as a live provider, etc.) may be reconsidered later. This vision **does not require them** for steady state if Docker secrets + SOPS + offline age-key backup meet the security bar.

## 5. Bootstrap experience (human, once per clone)

Prerequisite: Docker Swarm is already initialized and managers are available. (Node bring-up / hardening is out of scope for this spec.)

**Human does only:**

1. Point the local Docker CLI at a Swarm manager (Docker context) and confirm Swarm is ready.
2. Generate an age keypair for this clone/environment.
3. Create a Docker secret containing the age **private** key (for doco-cd / SOPS decrypt).
4. Store an offline backup of that private key in a highly secure location.
5. Provide git access material for doco-cd (e.g. deploy token or SSH key) as a Docker secret (or equivalent bootstrap-safe form).
6. Deploy **doco-cd** once from `bootstrap/doco-cd`.

**Platform then does:**

1. Poll the repo on an ongoing basis.
2. Decrypt SOPS-encrypted files with the cluster age key.
3. Deploy / reconcile Swarm stacks defined in git.
4. Create and rotate Docker secrets for applications (including Arcane and future apps).
5. Optionally self-update doco-cd from `bootstrap/doco-cd` when safe.

After step 6, no routine human `docker secret create` for app secrets should be required.

## 6. Developer and operations experience (day-2)

### 6.1 Add an application

1. Create `apps/<name>/` with `compose.yaml` and `secrets/` (SOPS-encrypted).
2. Encrypt secret files to the cluster age public key.
3. Commit and push.
4. doco-cd detects the change, deploys the stack, and materializes Docker secrets.

### 6.2 Change a service

1. Edit the app’s compose (or related config) in git.
2. Commit and push.
3. doco-cd reconciles the Swarm stack.

### 6.3 Rotate a secret

1. Update plaintext locally, re-encrypt with SOPS, commit.
2. doco-cd updates/rotates the corresponding Docker secret and redeploys consumers as needed.

### 6.4 Observe and debug

- Use **Arcane** and Docker CLI for status, logs, and inspection.
- Any durable fix or config change still lands as a git commit.

### 6.5 Clone for a new environment

1. Clone/fork the template into a new repo (or new remote) for that environment.
2. Generate a **new** age keypair for that environment (do not reuse private keys across clones).
3. Run the bootstrap checklist against that Swarm.
4. Adjust environment-specific values (URLs, replicas, etc.) in that clone’s git history.

## 7. Operational guardrails

- **Recoverable CD:** Even if doco-cd self-updates, `bootstrap/README.md` must describe how to redeploy doco-cd manually if the agent breaks itself.
- **Lost age key:** Restore private key from offline backup into Docker secrets; re-verify doco-cd decrypt works. If the key is compromised, rotate age keypair, re-encrypt all SOPS files, and redeploy.
- **Polling:** Steady state assumes doco-cd **polling** the git remote (webhooks may be added later; not required for the vision).
- **Scope creep:** Platform growth (proxy, monitoring, etc.) should follow the same app/bootstrap patterns and security policy rather than inventing a parallel control plane.

## 8. Out of scope (this vision)

- Provisioning or hardening Swarm nodes (cloud-init, IaC, OS baseline).
- Kubernetes or Nomad layouts in this repository.
- Multi-environment branches or multi-env directories inside one clone (rejected in favor of one env per clone).
- Making Arcane a desired-state author for stacks.
- Expanding the initial platform beyond doco-cd + Arcane (allowed later; not required for “vision complete”).

## 9. Success criteria

This vision is realized when:

1. A new environment can be stood up with the short bootstrap list above and no ongoing manual secret creation for apps.
2. Adding or changing an app is entirely a git workflow (compose + SOPS).
3. All app runtime secrets are Docker secrets.
4. Arcane is available for day-2 visibility without becoming a second source of truth.
5. The repo layout is understandable enough to clone as a starter for another Swarm environment.

## 10. Next step

After this spec is approved, produce an **implementation plan** (ordered tasks) to reshape the repo toward this layout and wire bootstrap → doco-cd → Arcane → secrets — without yet tackling node IaC.
