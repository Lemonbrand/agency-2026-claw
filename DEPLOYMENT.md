# Agency 2026 VPS Deployment

Production demo host:

- URL: `https://agency2026.lemonbrand.io/`
- Droplet: `agency2026-claw-demo`
- Region: `tor1`
- Public IP: `147.182.153.102`
- App path: `/opt/agency2026/site`
- Service: `agency2026.service`
- Reverse proxy: `nginx` on ports `80` and `443`

The app runs `node /opt/agency2026/site/server.js` behind nginx. Runtime secrets are stored server-side in `/etc/agency2026.env` and are not committed or served as static assets. HTTP redirects to HTTPS.

Useful checks:

```bash
ssh -i ~/.ssh/id_ed25519_nanoclaw root@147.182.153.102 "systemctl status agency2026 --no-pager"
curl https://agency2026.lemonbrand.io/api/health
curl -I https://agency2026.lemonbrand.io/env.local.json
```

TLS:

- Certificate: Let's Encrypt via certbot/nginx
- Expiry: `2026-07-28`
- Renewal: certbot scheduled renewal, dry run passed on deployment
