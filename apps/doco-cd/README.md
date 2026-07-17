# doco-cd

doco-cd is an application stack under `apps/`, managed from
[`compose.yaml`](compose.yaml). Ansible deploys it during greenfield bootstrap;
afterward, `.doco-cd.yaml` discovers and reconciles it with the other app
stacks.

Edit [`poll-config.yaml`](poll-config.yaml) to target this environment repo
before bootstrap. The required external Docker secrets are documented in
[`secrets/README.md`](secrets/README.md).

## Recovery

If doco-cd cannot reconcile itself, point a local Docker context at a Swarm
manager and redeploy it from the repository root:

```bash
docker stack deploy -c apps/doco-cd/compose.yaml doco-cd
```

Removing and redeploying the stack does not remove its external
`sops_age_key` and `git_access_token` Docker secrets.
