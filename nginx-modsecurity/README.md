# Nginx + ModSecurity

This directory contains the reverse-proxy, TLS, and log-panel access configuration for the production website stack.

At a high level, this subsystem is responsible for:

- terminating HTTPS
- proxying public traffic to the Flask app
- serving rendered article assets directly from Nginx
- exposing the Dozzle log UI behind Basic Auth
- keeping ModSecurity enabled for the public site while relaxing it for the internal log panel path

## Purpose

`nginx-modsecurity` sits in front of `web-app` and acts as the public entrypoint inside the VM.

It is the component that decides:

- which upstream service should receive a request
- which paths are served as static files
- which paths require extra authentication
- where WAF rules stay enabled or are explicitly disabled

## Main Behavior

The current routing behavior is defined in [conf.d/default.conf](/home/plain/personal-project/website/nginx-modsecurity/conf.d/default.conf).

### `/`

- proxied to `web-app:5000`
- forwards the usual proxy headers (`Host`, `X-Real-IP`, `X-Forwarded-*`)

### `/rendered-articles/`

- served directly from the rendered article directory through `alias`
- bypasses Flask for article body HTML assets and copied images

### `/web-log/`

- proxied to `dozzle:8080`
- protected with Nginx Basic Auth
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

### `ssl/hanjie-chen.com.key`

Private key file mounted into the container.

### `.htpasswd`

Basic Auth credentials used for `/web-log/`.

## Security Notes

- WAF stays enabled for the public site by default.
- `/web-log/` is the only intentionally relaxed path in the current config.
- Even though WAF is disabled on `/web-log/`, that endpoint is still protected with Basic Auth.
- Certificate and key management are external operational concerns; this directory only defines the mounted file locations expected by Nginx.

## Common Changes

### Change public proxy behavior

Start in:

- [conf.d/default.conf](/home/plain/personal-project/website/nginx-modsecurity/conf.d/default.conf)

### Change Dozzle access behavior

Check:

- [conf.d/default.conf](/home/plain/personal-project/website/nginx-modsecurity/conf.d/default.conf)
- [.htpasswd](/home/plain/personal-project/website/nginx-modsecurity/.htpasswd)

### Replace TLS material

Update:

- [ssl/hanjie-chen.com.crt](/home/plain/personal-project/website/nginx-modsecurity/ssl/hanjie-chen.com.crt)
- [ssl/hanjie-chen.com.key](/home/plain/personal-project/website/nginx-modsecurity/ssl/hanjie-chen.com.key)

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
- whether `.htpasswd` is present and correctly mounted
- whether the current config still preserves the upgrade / connection headers required for streaming

## Related Files

- [Readme.md](/home/plain/personal-project/website/Readme.md)
- [scripts/deploy/README.md](/home/plain/personal-project/website/scripts/deploy/README.md)
- [compose.yml](/home/plain/personal-project/website/compose.yml)
