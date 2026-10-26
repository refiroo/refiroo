#!/bin/sh
# Picks the server configuration the image's entrypoint then fills from the environment (0.12 DP2).
set -eu

case "${WEB_TLS:-files}" in
  files)
    if [ ! -r /certs/fullchain.pem ] || [ ! -r /certs/privkey.pem ]; then
      echo "web: WEB_TLS=files needs /certs/fullchain.pem and /certs/privkey.pem (the organisation's certificate and key)." >&2
      echo "web: Mount them, or set WEB_TLS=proxy when a load balancer in front ends HTTPS." >&2
      exit 1
    fi
    template=tls.conf.template ;;
  proxy) template=proxy.conf.template ;;
  *)
    echo "web: WEB_TLS must be 'files' or 'proxy', not '${WEB_TLS}'." >&2
    exit 1 ;;
esac
: "${PUBLIC_URL:?web: PUBLIC_URL, the address people open (for example https://rdm.example.org), is not set.}"

cp "/etc/nginx/templates-available/$template" /etc/nginx/templates/default.conf.template
echo "web: serving $PUBLIC_URL (WEB_TLS=${WEB_TLS:-files}), engine at $ENGINE_UPSTREAM"
