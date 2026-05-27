# FIXIT POS — Cloudflare DNS Configuration

## Domain: fixitsoluciones.com

The ERP (app.fixitsoluciones.com) already exists. These records are ONLY for FIXIT POS.

---

## DNS Records Required

### 1. Frontend — Production

| Type  | Name              | Content                  | Proxy Status | TTL  |
|-------|-------------------|--------------------------|--------------|------|
| CNAME | `pos`             | `cname.vercel-dns.com`   | Proxied (橙) | Auto |
| CNAME | `www.pos`         | `pos.fixitsoluciones.com`| Proxied (橙) | Auto |

### 2. Backend API — Production

| Type  | Name              | Content                        | Proxy Status | TTL  |
|-------|-------------------|--------------------------------|--------------|------|
| CNAME | `api-pos`         | `fixit-pos-api.onrender.com`   | Proxied (橙) | Auto |

### 3. Staging

| Type  | Name                   | Content                        | Proxy Status | TTL  |
|-------|------------------------|--------------------------------|--------------|------|
| CNAME | `staging-pos`          | `cname.vercel-dns.com`         | Proxied (橙) | Auto |
| CNAME | `api.staging-pos`      | `fixit-pos-api-staging.onrender.com` | Proxied (橙) | Auto |

### 4. Root Domain Wildcard (optional — for monitoring)

| Type  | Name              | Content                        | Proxy Status | TTL  |
|-------|-------------------|--------------------------------|--------------|------|
| CNAME | `status-pos`      | `status.fixitsoluciones.com`   | DNS only     | Auto |

---

## SSL/TLS Configuration

### Recommended Settings in Cloudflare Dashboard

| Setting                    | Value                          | Reason                                      |
|----------------------------|--------------------------------|---------------------------------------------|
| SSL/TLS encryption mode    | **Full (strict)**              | End-to-end encryption with valid origin cert|
| Minimum TLS Version        | **1.2**                        | Block TLS 1.0/1.1 (obsolete)               |
| Always Use HTTPS           | **On**                         | Redirect HTTP → HTTPS                       |
| HTTP Strict Transport      | **On**                         | `max-age=31536000; includeSubDomains; preload`|
| TLS 1.3                   | **On**                         | Enable modern protocol                      |
| Automatic HTTPS Rewrites   | **On**                         | Fix mixed content                           |
| Certificate Transparency  | **On**                         | Monitor cert issuance                       |

### Origin Certificate (for nginx/Caddy backend)

If using a self-hosted backend (not Render), generate an Origin Certificate:

1. Cloudflare Dashboard → SSL/TLS → Origin Server
2. Create Certificate
3. Select: `fixitsoluciones.com` and `*.fixitsoluciones.com`
4. Validity: 15 years
5. Copy the certificate + private key to your server:
   - `/etc/ssl/certs/fixitsoluciones.com.pem`
   - `/etc/ssl/private/fixitsoluciones.com.key`

---

## Recommended Security Settings

### WAF / Security Level

| Setting                    | Value                          |
|----------------------------|--------------------------------|
| Security Level             | **Medium** (High for /api/)    |
| Challenge Passage          | **30 minutes**                 |
| Browser Integrity Check    | **On**                         |
| Bot Fight Mode             | **On**                         |
| Rate Limiting              | Create rule for /api/v1/auth/login: 10 requests/minute per IP |

### Page Rules

| Rule                                               | Setting                          |
|----------------------------------------------------|----------------------------------|
| `pos.fixitsoluciones.com/api/*`                    | Cache Level: Bypass              |
| `pos.fixitsoluciones.com/_next/static/*`           | Cache Level: Standard, Edge Cache TTL: 30 days |
| `api-pos.fixitsoluciones.com/health`               | Cache Level: Bypass, Disable Security |

### Firewall Rules

| Rule Name                   | Field         | Operator  | Value                          | Action     |
|-----------------------------|---------------|-----------|--------------------------------|------------|
| Block non-POS origins       | HTTP Host     | contains  | `fixitsoluciones.com`          | Allow      |
| Block direct IP access      | HTTP Host     | matches   | `^\d+\.\d+\.\d+\.\d+$`        | Block      |
| Rate limit login             | URI Path      | contains  | `/api/v1/auth/login`           | Rate Limit: 10/min |

---

## Verification Checklist

After configuring DNS:

- [ ] `dig pos.fixitsoluciones.com` returns CNAME to `cname.vercel-dns.com`
- [ ] `dig api-pos.fixitsoluciones.com` returns CNAME to `fixit-pos-api.onrender.com`
- [ ] `dig staging-pos.fixitsoluciones.com` returns CNAME to `cname.vercel-dns.com`
- [ ] SSL/TLS shows **Full (strict)** in Cloudflare dashboard
- [ ] Browser shows padlock when visiting `https://pos.fixitsoluciones.com`
- [ ] `curl -I https://api-pos.fixitsoluciones.com/health` returns 200
- [ ] CORS preflight works: `curl -X OPTIONS -H "Origin: https://pos.fixitsoluciones.com" https://api-pos.fixitsoluciones.com/api/v1/products/search`
- [ ] Vercel deployment shows custom domain `pos.fixitsoluciones.com`
- [ ] Render service shows custom domain `api-pos.fixitsoluciones.com`

---

## Troubleshooting

### CORS errors in browser

Check the `Access-Control-Allow-Origin` response header matches the requesting origin exactly:
```bash
curl -I -H "Origin: https://pos.fixitsoluciones.com" \
  https://api-pos.fixitsoluciones.com/api/v1/products/search
```

### DNS not propagating

```bash
# Check Cloudflare proxy status
dig +short pos.fixitsoluciones.com
# Should show Cloudflare IPs (104.x.x.x or 172.x.x.x) if proxied
# Should show CNAME target if DNS-only

# Force flush local DNS
sudo dscacheutil -flushcache  # macOS
sudo systemd-resolve --flush-caches  # Linux
ipconfig /flushdns  # Windows
```

### Vercel domain not working

- Go to Vercel Dashboard → Project → Settings → Domains
- Add `pos.fixitsoluciones.com`
- Verify DNS configuration in Vercel (green checkmark)
- Ensure Cloudflare proxy is **ON** (orange cloud) for Vercel domains
