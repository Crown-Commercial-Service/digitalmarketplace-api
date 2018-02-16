#!/bin/bash

eval $(./scripts/ups_as_envs.py)
exec celery -A 'app.tasks' worker -l info -B -s "/tmp/celerybeat-schedule"
