We use letsencrypt to issue SSL certs for our domains.

# Step 1. graph.castN.k3l.io

Example, graph.cast9.k3l.io. This sub-domain is not load-balanced but is very useful when we want to simulate a blue-green deployment. Also, setting up this sub-domain also makes the next step simple.

A typical crontab to both **install** as well as **renew** certs looks like this:
``` 
1 0 */7 * * sudo certbot run --nginx -d graph.cast9.k3l.io -m ops@karma3labs.com --agree-tos -n
```
This crontab assumes that `/etc/nginx/sites-available/` is aleady configured for the sub-domain name.

This repo has a sample nginx file that you can use. **REMEMBER** to replace `N` with your preferred number. 
Also, **REMEMBER** to soft link the config file `sudo ln -s /etc/nginx/sites-available/graph.castN.k3l.io /etc/nginx/sites-enabled/` 
**NOTE** the sample file does not have ssl config because certbot will add the appropriate config when certbot is run for the first time `sudo certbot run --nginx -d graph.castN.k3l.io -m ops@karma3labs.com --agree-tos -n`

# Step 2. graph.cast.k3l.io
The sub-domain `graph.cast.k3l.io` is load-balanced across multiple machines. When renewing certs, we cannot have certs renewed from multiple machines and have them invalidate the others. So, we renew certs on 1 machine and push the cert to all the other machines. 

The `install_certs.sh` script takes care of renewing the cert while `push_certs.sh` pushes the cert to the other machines.

#### Pre-req
`/etc/nginx/sites-available/` should have a config for `graph.cast.k3l.io`

This repo has a sample nginx file that you can use. **REMEMBER** to replace `CHANGME_OPENSSL_RAND_KEY` with a strong api key. Also, **REMEMBER** to soft link the config file `sudo ln -s /etc/nginx/sites-available/graph.cast.k3l.io /etc/nginx/sites-enabled/`

#### Cronjobs
A typical crontab on the **"primary"** host looks like this: 
```
15 0 */7 * * sudo certbot run --nginx -d graph.cast.k3l.io -m ops@karma3labs.com --agree-tos -n >> /var/log/farcaster-graph/graphcast_jobs.log 2>&1; sudo nginx -s reload >> /var/log/farcaster-graph/graphcast_jobs.log 2>&1; date >> /var/log/farcaster-graph/graphcast_jobs.log ; cd /home/ubuntu/graphcast_jobs; ./push_certs.sh -h 162.55.109.106 >> /var/log/farcaster-graph/graphcast_jobs.log 2>&1;
```
1. renew cert `sudo certbot run --nginx -d graph.cast.k3l.io -m ops@karma3labs.com --agree-tos -n`
2. reload nginx locally to make sure cert is fine `sudo nginx -s reload`
3. push renewed cert to 162.55.109.106 `./push_certs.sh -h 162.55.109.106`

And, the crontab on the **"secondary"** host looks like this:
```
30 0 */7 * * date >> /var/log/farcaster-graph/graphcast_jobs.log ; cd /home/ubuntu/graphcast_jobs; ./install_certs.sh >> /var/log/farcaster-graph/graphcast_jobs.log 2>&1
```
1. install cert assuming that graph.cast.k3l.io nginx config already exists and the "primary" server has scp'd over the pem files.