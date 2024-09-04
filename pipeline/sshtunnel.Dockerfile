FROM alpine:3.8

RUN apk add --no-cache autossh libressl

RUN mkdir -p ~/.ssh

ENTRYPOINT ["/usr/bin/autossh", \
  "-M", "0", "-T", "-N", "-g", "-v", \
  "-oStrictHostKeyChecking=no", \
  "-oServerAliveInterval=180", \
  "-oUserKnownHostsFile=/dev/null", \
  "-oGlobalKnownHostsFile=/dev/null", \
  "-i/root/.ssh/id_rsa"]