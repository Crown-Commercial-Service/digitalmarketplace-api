#!/bin/sh

set -e

# The existing service broker generates random credentials on binding.  dm-api was the original app and therefore has
# the credentials for our original data; dm-api-blue was added later.  It would be neat to use a second app called
# dm-api-green to match the other deployments, but we need to keep dm-api to keep the original binding.  Hopefully we'll
# get a broker with better behaviour someday.
# More background is in this thread (note that this is a different broker with different behaviour and other problems):
# https://github.com/18F/aws-broker/issues/12

cf target -o dto -s digital-marketplace
cf push ${APP_GROUP}-migrate -c 'python application.py db upgrade' -u 'none' -i 1
APP=${APP_GROUP} DOMAIN=apps.$ENVIRONMENT.digital.gov.au HOSTNAME=${APP_GROUP} ./scripts/cf_ha_deploy.sh
APP=${APP_GROUP}-blue DOMAIN=apps.$ENVIRONMENT.digital.gov.au HOSTNAME=${APP_GROUP} ./scripts/cf_ha_deploy.sh
