#!/bin/sh

# Exit immediately if any commands return non-zero
set -e
# Output the commands we run
set -x
# download cf-cli and use to push
curl -v -L -o cf-cli_amd64.deb 'https://cli.run.pivotal.io/stable?release=debian64&source=github'
sudo dpkg -i cf-cli_amd64.deb
cf -v
cf login -a https://api.system.staging.digital.gov.au -o dto -u $CF_USER_STAGING -p $CF_PASSWORD_STAGING
cf target -o dto -s digital-marketplace
cf push