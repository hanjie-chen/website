# Nginx + ModSecurity

HTTPS termination, reverse proxy, rendered article assets and the Dozzle log
panel for the website. The OWASP CRS image and container settings are declared
in [compose.yml](../compose.yml).

## Configuration and TLS

[conf.d/default.conf](conf.d/default.conf) is mounted as
`/etc/nginx/templates/conf.d/default.conf.template` for the container image to
render at startup. Edit the repository template and recreate the service to
apply template changes; a reload alone does not regenerate the mounted template.

The `ssl/` directory is mounted read-only at `/etc/nginx/ssl`. Provide
`hanjie-chen.com.crt` and `hanjie-chen.com.key` there with permissions readable by
the container. Production uses Cloudflare Origin CA material according to the
repository's deployment setup; local development can use self-signed material.
Certificate issuance and Cloudflare TLS settings are managed outside this config.

Production exposes ports 80/443. The [development overlay](../compose.dev.yml)
uses 8081/8444; use `https://127.0.0.1:8444` directly for local checks because the
HTTP redirect does not add the development HTTPS port.

## Routing

| Location | Destination / behavior |
| --- | --- |
| HTTP port 80 | Redirect to `https://$host$request_uri` |
| HTTPS `/` | Proxy to `web-app:5000`, forwarding Host and client/protocol headers |
| `/rendered-articles/` | Serve generated HTML and copied assets from the shared volume through `alias`; directory listing disabled |
| Exact `/internal/briefs` | Proxy to Flask with a 128 KiB body limit and WAF disabled |
| Prefix `/web-log/` | Proxy to `dozzle:8080` with WAF disabled, buffering off and WebSocket/streaming headers |

Dozzle's `DOZZLE_BASE=/web-log` setting in Compose must stay aligned with its
proxy path. Other paths, including `/static/` and `/internal/reindex`, use the
normal Flask proxy location.

Upstream addresses use variables so Nginx can resolve container names at request
time through the resolver supplied by the base image. Keep this behavior when
changing proxy rules; container IPs can change after recreation.

## Security Notes

WAF protection is enabled by the image's default configuration, with two explicit
exceptions in the site template:

- **Daily Brief publishing:** only the exact `/internal/briefs` location bypasses
  generic SQLi/XSS signatures, which can reject technical prose stored as text.
  Nginx limits request bodies; Flask requires an independent token and validates
  schema, field bounds and URLs before storage. Templates escape brief content.
  The application does not execute submitted text or fetch submitted URLs.
  See the [publishing contract](../web-app/README.md#publishing-api).
- **Dozzle:** `/web-log/` bypasses WAF to support log queries and streams. Access
  protection relies on the separately managed Cloudflare Access policy. This
  Nginx configuration does not enforce Basic Auth or validate Access tokens.

The `/internal/` prefix is not network isolation. Origin reachability and
Cloudflare policies must preserve the intended access boundary; the repository
configuration alone does not establish the current edge settings.

### Audit Logging

Compose sends ModSecurity audit records to `/proc/self/fd/2` with parts `AHZ`,
making them available through Docker logs and Dozzle. Full request headers and
bodies are omitted to reduce token and content exposure. Rule messages can still
include matched fragments, so logs remain sensitive operational data.

Docker JSON logs rotate at `max-size: 1m`, `max-file: 5` per container. Detailed
request bodies should not be enabled merely to diagnose a blocked request.

## Validation and Troubleshooting

Run from the repository root against a prepared, running stack:

```bash
docker compose exec -T nginx-modsecurity nginx -t
docker compose ps
docker compose logs --tail=120 nginx-modsecurity web-app
```

| Symptom | Check |
| --- | --- |
| Nginx fails to start | Generated config, TLS file presence/permissions and upstream resolution |
| `502` response | Web-app state/logs and container DNS; inspect with `docker compose exec -T nginx-modsecurity getent hosts web-app` |
| Publishing `403` | Identify whether Cloudflare or the origin returned it; for requests reaching Flask through the exact publishing location, check the publishing token |
| Publishing `413` | Request body exceeds the configured limit |
| Log panel unavailable | Dozzle health, `DOZZLE_BASE`, proxy streaming headers and the external Cloudflare Access policy |

Do not print publishing tokens while diagnosing authentication. Application
validation/status semantics are documented in the publishing contract.

The Compose health check requests local HTTPS `/` with certificate verification
skipped. It does not verify Cloudflare policies or public TLS validity. For
broader checks and the side effects of optional publishing probes, see
[deployment validation](../scripts/deploy/README.md#smoke-check-boundaries).

## Image Updates

Compose pins the Nginx/ModSecurity image by tag and digest. Candidate validation
includes `nginx -t`, service health and runtime smoke checks. Image policy and
exceptions belong in the [security guide](../scripts/security/README.md);
CI/CD orchestration belongs in the [workflow guide](../.github/workflows/README.md).
Production reload/recreation and limited third-party image rollback are covered
by the [deployment guide](../scripts/deploy/README.md#database-repair-and-rollback).
