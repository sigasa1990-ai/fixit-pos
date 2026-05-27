# =============================================================================
# FIXIT POS — Backend API
# api-pos.fixitsoluciones.com → Render (proxy passthrough)
# =============================================================================

upstream fixit_backend {
    server fixit-pos-api.onrender.com:443;
    keepalive 32;
}

server {
    listen 80;
    server_name api-pos.fixitsoluciones.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api-pos.fixitsoluciones.com;

    # SSL
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
    add_header Cache-Control "no-store, no-cache, must-revalidate" always;
    add_header Pragma "no-cache" always;

    # CORS headers for preflight
    add_header Access-Control-Allow-Origin $http_origin always;
    add_header Access-Control-Allow-Methods "GET, POST, PATCH, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Correlation-ID, X-Idempotency-Key, X-Tenant-ID" always;
    add_header Access-Control-Allow-Credentials "true" always;
    add_header Access-Control-Expose-Headers "X-Correlation-ID, X-Request-ID" always;
    add_header Access-Control-Max-Age "86400" always;

    # Handle CORS preflight
    if ($request_method = OPTIONS) {
        add_header Access-Control-Allow-Origin $http_origin;
        add_header Access-Control-Allow-Methods "GET, POST, PATCH, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Correlation-ID, X-Idempotency-Key, X-Tenant-ID";
        add_header Access-Control-Allow-Credentials "true";
        add_header Access-Control-Max-Age "86400";
        add_header Content-Length 0;
        add_header Content-Type text/plain;
        return 204;
    }

    # API proxy
    location / {
        proxy_pass https://fixit-pos-api.onrender.com;
        proxy_http_version 1.1;
        proxy_set_header Host fixit-pos-api.onrender.com;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Original-Host $host;
        proxy_read_timeout 120s;
        proxy_send_timeout 60s;
        proxy_connect_timeout 30s;

        # Buffering for API responses
        proxy_buffering on;
        proxy_buffer_size 8k;
        proxy_buffers 8 8k;
        proxy_busy_buffers_size 16k;

        # Pass original host for CORS
        proxy_set_header Origin $http_origin;
    }

    # Health check does not need buffering
    location /health {
        proxy_pass https://fixit-pos-api.onrender.com/health;
        proxy_http_version 1.1;
        proxy_set_header Host fixit-pos-api.onrender.com;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        access_log off;
    }

    # Block common exploits
    location ~* (\.env|\.git|composer\.json|package\.json|yarn\.lock) {
        deny all;
        return 404;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
    limit_req zone=api_limit burst=50 nodelay;

    # Limit login endpoint
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/s;
    location /api/v1/auth/login {
        limit_req zone=login_limit burst=10 nodelay;
        proxy_pass https://fixit-pos-api.onrender.com/api/v1/auth/login;
        proxy_http_version 1.1;
        proxy_set_header Host fixit-pos-api.onrender.com;
    }

    access_log /var/log/nginx/api-pos.fixitsoluciones.com.access.log;
    error_log  /var/log/nginx/api-pos.fixitsoluciones.com.error.log;
}
