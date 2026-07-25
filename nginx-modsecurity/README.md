# Nginx + ModSecurity

This directory contains the reverse-proxy, TLS, and log-panel access configuration for the production website stack.

At a high level, this subsystem is responsible for:

- terminating HTTPS
- proxying public traffic to the Flask app
- serving rendered article assets directly from Nginx
- exposing the Dozzle log UI behind Cloudflare Access
- keeping ModSecurity enabled for the public site while relaxing it for the internal log panel path
- applying narrow CRS false-positive exclusions to authenticated Daily Brief JSON ingestion

## Purpose

`nginx-modsecurity` sits in front of `web-app` and acts as the public entrypoint inside the VM.

It is the component that decides:

- which upstream service should receive a request
- which paths are served as static files
- which paths require extra authentication
- where WAF rules stay enabled or are explicitly disabled

## Main Behavior

The current routing behavior is defined in [conf.d/default.conf](conf.d/default.conf).

### `/`

- proxied to `web-app:5000`
- forwards the usual proxy headers (`Host`, `X-Real-IP`, `X-Forwarded-*`)

### `/rendered-articles/`

- served directly from the rendered article directory through `alias`
- bypasses Flask for article body HTML assets and copied images

### `/internal/briefs`

- remains behind ModSecurity and is proxied to Flask like the rest of the public site
- requires the application-level `X-DAILY-BRIEF-TOKEN`
- loads `modsecurity/briefs-exclusions.conf`, which removes only CRS rules `941100`, `941110`, and `941160` for this exact path
- those three XSS rules are false positives for legitimate summaries that discuss literal `<script>` examples; all other CRS rules remain active, and Flask strictly validates and later escapes every stored field

### `/web-log/`

- proxied to `dozzle:8080`
- currently protected by Cloudflare Access at the edge
- WebSocket / streaming related headers are preserved
- ModSecurity is explicitly turned off for this path because Dozzle log queries and streams are noisy enough to trigger CRS rules

### `80 -> 443`

- plain HTTP is only used for redirecting to HTTPS

## Why The Upstreams Use Variables

The config uses:

- `set $webapp_upstream "http://web-app:5000";`
- `set $dozzle_upstream "http://dozzle:8080";`

instead of hardcoding `proxy_pass http://web-app:5000;`.

This is intentional.

It helps Nginx re-resolve container DNS instead of holding onto a stale container IP after a service restart or recreation. This matters for Docker Compose environments where container IPs can change across deploys.

## Important Files

### `conf.d/default.conf`

Primary Nginx server config for:

- HTTPS termination
- reverse proxy behavior
- static article asset serving
- Dozzle path protection

### `modsecurity/briefs-exclusions.conf`

Pre-CRS exclusion rules for confirmed Daily Brief JSON false positives. Keep exclusions scoped to an exact endpoint and specific rule IDs; do not disable ModSecurity for `/internal/briefs`.

### `ssl/hanjie-chen.com.crt`

Certificate file mounted into the container.
In production this path is intended for the Cloudflare Origin CA certificate.
In development it can be a self-signed certificate.

### `ssl/hanjie-chen.com.key`

Private key file mounted into the container.

## Security Notes

- WAF stays enabled for the public site by default.
- `/web-log/` is the only intentionally relaxed path in the current config.
- `/internal/briefs` keeps WAF processing enabled with only three endpoint-scoped XSS false-positive exclusions.
- Even though WAF is disabled on `/web-log/`, that endpoint is currently protected by Cloudflare Access.
- Production currently uses Cloudflare Origin CA material at the mounted TLS paths.
- Development can use self-signed TLS material at the same paths.

## Image Lifecycle

Production does not follow the mutable `nginx-alpine` rolling tag. The Compose
service uses an OWASP CRS stable tag together with its immutable multi-platform
digest.

Container image updates follow this path:

1. Dependabot proposes a tag/digest update in a pull request.
2. CI scans the candidate with Trivy, validates `nginx -t`, starts the candidate
   runtime, and runs health and smoke checks.
3. After merge, CD explicitly pulls the pinned reference and recreates the
   changed service.
4. CD verifies that the running image reference exactly matches `compose.yml`.
5. A failed post-deploy validation restores the previously running Nginx and
   Dozzle image references.

The scheduled container-security workflow rescans the pinned image every day.
Temporary risk acceptances live in `.trivyignore.yaml` and must include a reason
and an expiry date.

## Common Changes

### Change public proxy behavior

Start in:

- [conf.d/default.conf](conf.d/default.conf)

### Change Dozzle access behavior

Check:

- [conf.d/default.conf](conf.d/default.conf)

Also consider the matching Cloudflare Access application for `/web-log/*`, because the effective production protection now lives at the edge layer.

### Replace TLS material

Update:

- [ssl/hanjie-chen.com.crt](ssl/hanjie-chen.com.crt)
- [ssl/hanjie-chen.com.key](ssl/hanjie-chen.com.key)

## Troubleshooting

### Nginx container does not become healthy

Start with:

```bash
docker compose logs --tail=200 nginx-modsecurity
```

Common causes:

- invalid Nginx config syntax
- missing upstream service
- missing or unreadable certificate/key files

### Public site returns `502`

Start with:

```bash
docker compose ps
docker compose logs --tail=120 nginx-modsecurity web-app
docker compose exec -T nginx-modsecurity getent hosts web-app
```

If the proxy is holding onto a stale upstream state after service recreation, reloading or restarting Nginx is the first thing to try.

### `/web-log/` stops working

Check:

- whether `dozzle` is healthy and reachable
- whether Cloudflare Access policy still matches `/web-log/*`
- whether the current config still preserves the upgrade / connection headers required for streaming

## Related Files

- [README.md](../README.md)
- [scripts/deploy/README.md](../scripts/deploy/README.md)
- [compose.yml](../compose.yml)
