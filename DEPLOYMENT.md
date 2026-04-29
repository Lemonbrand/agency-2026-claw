# Agency 2026 VPS Deployment

Production demo host:

- Droplet: `agency2026-claw-demo`
- Region: `tor1`
- Public IP: `147.182.153.102`
- App path: `/opt/agency2026/site`
- Service: `agency2026.service`
- Reverse proxy: `nginx` on port `80`

The app runs `node /opt/agency2026/site/server.js` behind nginx. Runtime secrets are stored server-side in `/etc/agency2026.env` and are not committed or served as static assets.

Useful checks:

```bash
ssh -i ~/.ssh/id_ed25519_nanoclaw root@147.182.153.102 "systemctl status agency2026 --no-pager"
curl http://147.182.153.102/api/health
curl -I http://147.182.153.102/env.local.json
```

DNS handoff:

- Point `agency2026.lemonbrand.io` to `147.182.153.102`.
- Current nameservers for `lemonbrand.io` are Namecheap registrar servers, so the A record needs to be set there unless DNS is moved.
- After DNS resolves, add TLS with certbot or the existing preferred proxy pattern.
