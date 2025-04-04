# Allow listed IP addresses with no rate limits
geo $is_internal {
    default 0;
    10.0.0.0/8 1;
    127.0.0.1/32 1;
    172.17.0.0/24 1;
    192.168.0.0/24 1;
}

# Define a map for internal unlimited API keys
map $http_api_key $is_valid_internal_api {
    default 0;
    "CHANGEME_OPENSSL_RAND_KEY" 1;  # FOR INTERNAL USE ONLY
}

# Define a map for high-rate-limit API keys
map $http_api_key $is_valid_api_key {
    default 0;
    "CHANGEME_OPENSSL_RAND_KEY" 1;  # for Automod
    "CHANGEME_OPENSSL_RAND_KEY" 1;  # reserved for future use
    "CHANGEME_OPENSSL_RAND_KEY" 1;  # reserved for future use
    # Add more API keys as needed into zone 1
}

# If not valid api key, return IP so regular_zone can throttle
# If valid api key, just return empty string so that regular_zone won't apply
map $is_valid_api_key $regular_ip {
    0 $binary_remote_addr;
    1 "";
}


# Specify 10 MB storage of binary IP addresses to keep track of 1.6 mil addresses
limit_req_zone $binary_remote_addr zone=high_zone:10m rate=100r/s;
limit_req_zone $regular_ip zone=regular_zone:10m rate=10r/s;
limit_req_status 429;

server {
    server_name graph.cast.k3l.io;

    access_log /var/log/nginx/access.log combined if=$is_valid_api_key;
    access_log /var/log/nginx/pri-access.log combined if=$is_valid_api_key;

    location ~* \.(env|git|bak|config|log|sh)$ {
        deny all;
        return 404;
    }

    location ~ ^/(_pause|_resume) {
        return 404;
    }

    # Location for internal unlimited calls
    location ~ ^/internal/.* {
        if ($is_valid_internal_api = 0) {
            return 403;
        }
        rewrite ^/internal/(.*)$ /$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Location for high rate limiting
    location ~ ^/priority/.* {
        if ($is_valid_api_key = 0) {
            return 403;
        }
        limit_req zone=high_zone burst=100 nodelay;
        rewrite ^/priority/(.*)$ /$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Root location without rate limiting
    location / {
        limit_req zone=regular_zone burst=1 nodelay;
        limit_req zone=high_zone burst=100 nodelay;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    error_page 503 429 = @ratelimit;

    location @ratelimit {
        return 429 "Too Many Requests";
    }

    error_page 403 = @forbidden;

    location @forbidden {
        return 403 "Forbidden: Invalid API Key";
    }

    listen 443 ssl; 
    ssl_certificate /etc/letsencrypt/live/graph.cast.k3l.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/graph.cast.k3l.io/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf; 
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; 

}

server {
    server_name graph.cast.k3l.io;

    location ~* \.(woff|jpg|jpeg|png|gif|ico|css|js)$ {
        access_log off;
    }

    if ($host = graph.cast.k3l.io) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    return 404;
}
