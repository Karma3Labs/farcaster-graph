# Allow listed IP addresses with no rate limits
geo $limit {
    default 1;
    10.0.0.0/8 0;
    127.0.0.1/32 0;
    192.168.0.0/24 0;
}

map $limit $limit_key {
    0 "";
    1 $binary_remote_addr;
}

# Specify 10 MB storage of binary IP addresses to keep track of 1.6 mil addresses
# to limit at 5 requests/second
limit_req_zone $limit_key zone=graph_castN_zone:10m rate=5r/s;

server {
    server_name graph.castN.k3l.io;

    location ~ ^/(_pause|_resume) {
	return 404;
    }

    location / {
	# apply rate limit
	limit_req zone=graph_castN_zone burst=10;
	proxy_pass http://localhost:8000;
	proxy_http_version 1.1;
	proxy_set_header Upgrade $http_upgrade;
	proxy_set_header Connection 'upgrade';
	proxy_set_header Host $host;
	proxy_cache_bypass $http_upgrade;
    }

    listen 443 ssl; 
    ssl_certificate /etc/letsencrypt/live/graph.castN.k3l.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/graph.castN.k3l.io/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf; 
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; 
}

server {
    server_name graph.castN.k3l.io;

    location ~* \.(woff|jpg|jpeg|png|gif|ico|css|js)$ {
      access_log off;
    }
    if ($host = graph.cast4.k3l.io) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    return 404;
}
