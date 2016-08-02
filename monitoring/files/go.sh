#!/bin/bash

set -e

/usr/bin/confd -onetime -backend=env

exec /opt/sensu/embedded/bin/ruby /opt/sensu/bin/sensu-client \
-c /etc/sensu/config.json \
-d /etc/sensu/conf.d \
-e /etc/sensu/extensions \
-L info
