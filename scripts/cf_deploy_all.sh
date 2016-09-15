#!/bin/sh

set -e

cf target -o dto -s digital-marketplace
cf push ${APP_GROUP}-migrate -c 'python application.py db upgrade' -u 'none' -i 1
APP=${APP_GROUP}-green DOMAIN=apps.$ENVIRONMENT.digital.gov.au HOSTNAME=${APP_GROUP} ./scripts/cf_ha_deploy.sh
APP=${APP_GROUP}-blue DOMAIN=apps.$ENVIRONMENT.digital.gov.au HOSTNAME=${APP_GROUP} ./scripts/cf_ha_deploy.sh
