# Apps

Related: [Ansible bootstrap design](ansible-bootstrap.md) · [Security policy](security-policy.md) · [bootstrap/README.md](../bootstrap/README.md)

## Add an app

1. Create `apps/<name>/compose.yaml` (Swarm-compatible compose).
2. Put secret payloads under `apps/<name>/secrets/` and encrypt with SOPS using the cluster public key in `age.pubkey` / `.sops.yaml`.
3. Reference secret files from compose (`secrets:` → `file: ./secrets/...`).
4. Commit and push. doco-cd auto-discovers directories under `apps/` (see `.doco-cd.yaml`).

## Expose an app through Traefik

Do **not** publish host ports on app services. Only Traefik binds `80`/`443`.

1. Attach the service to the shared overlay network (created by `apps/traefik`):

   ```yaml
   networks:
     traefik-public:
       external: true
   ```

   And under the service:

   ```yaml
   networks:
     - traefik-public
     # ...plus any app-private networks
   ```

2. Add Swarm **deploy** labels (Traefik reads these in swarm mode), including the container listen port:

   ```yaml
   deploy:
     labels:
       traefik.enable: "true"
       traefik.swarm.network: "traefik-public"
       traefik.http.routers.<name>.rule: "Host(`app.example.com`)"
       traefik.http.routers.<name>.entrypoints: "web"
       traefik.http.services.<name>.loadbalancer.server.port: "<container-port>"
   ```

3. If the app has a public URL env var (e.g. Arcane `APP_URL`), set it to the same host Traefik serves (scheme `http` on entrypoint `web` until TLS is added).

`apps/traefik` must be deployed before apps that declare `traefik-public` as `external: true`. After the first successful Traefik deploy, doco-cd can reconcile the rest.

## Change a service

Edit compose → commit → push. doco-cd reconciles the stack.

## Rotate a secret

1. `sops edit apps/<name>/secrets/<file>` (or re-encrypt).
2. Commit and push. doco-cd rotates Docker secrets (content hash suffix) and redeploys consumers.

## Observe

Use Arcane and the `docker` CLI with your Swarm Docker context selected (see [bootstrap/README.md](../bootstrap/README.md) Step 1). Durable fixes still go through git.
