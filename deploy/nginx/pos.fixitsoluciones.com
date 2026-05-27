# =============================================================================
# FIXIT POS — Frontend
# pos.fixitsoluciones.com → Vercel (proxy passthrough)
# =============================================================================

server {
    listen 80;
    server_name pos.fixitsoluciones.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pos.fixitsoluciones.com;

    # SSL (Cloudflare Edge Certificates or Let's Encrypt)
    ssl_certificate     /etc/ssl/certs/fixitsoluciones.com.pem;
    ssl_certificate_key /etc/ssl/private/fixitsoluciones.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Content-Security-Policy "
        default-src 'self';
        script-src 'self' 'unsafe-inline' 'unsafe-eval';
        style-src 'self' 'unsafe-inline';
        img-src 'self' data: https:;
        font-src 'self' data:;
        connect-src 'self' https://api-pos.fixitsoluciones.com https://staging-pos.fixitsoluciones.com wss://localhost:9100;
        frame-ancestors 'none';
        form-action 'self';
    " always;

    # Proxy to Vercel
    location / {
        proxy_pass https://fixit-pos.vercel.app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host fixit-pos.vercel.app;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Original-Host $host;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;

        # Disable buffering for streaming
        proxy_buffering off;
        proxy_cache off;
    }

    # Block common exploits
    location ~* (\.env|\.git|composer\.json|package\.json|yarn\.lock) {
        deny all;
        return 404;
    }

    access_log /var/log/nginx/pos.fixitsoluciones.com.access.log;
    error_log  /var/log/nginx/pos.fixitsoluciones.com.error.log;
}
