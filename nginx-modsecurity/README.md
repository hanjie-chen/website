# Nginx + ModSecurity

This directory contains the reverse-proxy, TLS, and log-panel access configuration for the production website stack.

At a high level, this subsystem is responsible for:

- terminating HTTPS
- proxying public traffic to the Flask app
- serving rendered article assets directly from Nginx
- exposing the Dozzle log UI behind Cloudflare Access
- keeping ModSecurity enabled for the public site while relaxing it only for exact paths with stronger application-specific controls

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

- uses an exact-match Nginx location and is proxied to Flask with ModSecurity disabled only for this endpoint
- rejects bodies larger than 128 KiB at Nginx before they reach Flask
- requires the application-level `X-DAILY-BRIEF-TOKEN`
- accepts technical prose as opaque text instead of applying generic SQLi/XSS signatures to the JSON body
- relies on the application trust boundary: constant-time token comparison, exact schema and field limits, safe date-derived storage paths, HTTP(S)-only URLs, and Jinja escaping
- does not execute the submitted text, interpolate it into SQL or shell commands, or fetch submitted URLs server-side

This exception is based on data flow, not on the word `internal`: the endpoint is still Internet-reachable. A leaked token would be an authorization incident that a generic WAF could not prevent, so keep the token random, secret, and independently rotatable.

### Audit logging

- ModSecurity writes metadata-only JSON audit records to `/proc/self/fd/2`, so they are available through Docker logs and Dozzle
- audit parts are limited to `AHZ`; full request headers and bodies are intentionally omitted so `X-DAILY-BRIEF-TOKEN` is not copied into audit records and brief-content exposure is minimized
- rule messages can still contain the small matched fragment needed to explain a block; treat the log stream as security-sensitive operational data
- Compose log rotation limits each container to five 1 MiB files

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

### `ssl/hanjie-chen.com.crt`

Certificate file mounted into the container.
In production this path is intended for the Cloudflare Origin CA certificate.
In development it can be a self-signed certificate.

### `ssl/hanjie-chen.com.key`

Private key file mounted into the container.

## Security Notes

- WAF stays enabled for the public site by default.
- `/web-log/` and the exact `/internal/briefs` location are the only intentionally relaxed paths in the current config.
- `/internal/briefs` compensates for its WAF bypass with an Nginx 128 KiB limit plus application-level authentication, strict validation, safe storage, and output escaping. The WAF remains active on every other route.
- audit logs omit full request headers and bodies to keep internal tokens out of the container log stream and minimize unpublished-content exposure; individual rule messages may still include a matched fragment.
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

### Daily Brief publishing returns `403`

Because ModSecurity is disabled only on the exact ingestion location, a `403` from this endpoint is the Flask token check rather than a CRS anomaly block. Confirm that the publisher and website use the same token, then inspect the application and proxy logs:

```bash
docker compose logs --tail=200 web-app nginx-modsecurity
```

Do not print the token itself. A payload larger than 128 KiB returns `413`; invalid JSON or schema returns `400` after successful authentication.

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
