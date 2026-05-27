# =============================================================================
# FIXIT POS — Staging (proxy to staging backend + frontend)
# staging-pos.fixitsoluciones.com
# =============================================================================

server {
    listen 80;
    server_name staging-pos.fixitsoluciones.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name staging-pos.fixitsoluciones.com;

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
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Basic auth for staging
    auth_basic "FIXIT POS Staging";
    auth_basic_user_file /etc/nginx/.htpasswd-staging;

    # Frontend static files
    root /var/www/staging-pos/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;

        # API proxy
        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 60s;
        }
    }

    location /_next/static/ {
        alias /var/www/staging-pos/frontend/_next/static/;
        expires 365d;
        add_header Cache-Control "public, immutable";
    }

    # Health
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        auth_basic off;
    }

    access_log /var/log/nginx/staging-pos.fixitsoluciones.com.access.log;
    error_log  /var/log/nginx/staging-pos.fixitsoluciones.com.error.log;
}
