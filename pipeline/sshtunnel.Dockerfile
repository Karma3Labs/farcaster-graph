FROM alpine:3.8

ARG USER=autossh
ARG GROUP=autossh
ARG UID=1024
ARG GID=1024

RUN addgroup -S -g ${GID} ${GROUP} \
  && adduser -S -D -H -s /bin/false -g "${USER} service" \
  -u ${UID} -G ${GROUP} ${USER} \
  && set -x \
  && apk add --no-cache autossh libressl

USER ${USER}

ENTRYPOINT ["/usr/bin/autossh", \
  "-M", "0", "-T", "-N", "-g", "-v", \
  "-oStrictHostKeyChecking=no", \
  "-oServerAliveInterval=180", \
  "-oUserKnownHostsFile=/dev/null", \
  "-oGlobalKnownHostsFile=/dev/null", \
  "-i/.ssh/id_rsa"]