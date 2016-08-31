#!/bin/sh

set -ex

cf unmap-route "$APP" "$DOMAIN" --hostname "$HOSTNAME"
cf push "$APP" -f "$MANIFEST"
cf map-route "$APP" "$DOMAIN" --hostname "$HOSTNAME"
