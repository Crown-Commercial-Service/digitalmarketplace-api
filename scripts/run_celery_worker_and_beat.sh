#!/bin/bash
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Already in virtual environment $VIRTUAL_ENV"
else
  source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."
fi


[[ "$CELERY_BEAT_SCHEDULE_FILE" ]] \
    && BEATDB="$CELERY_BEAT_SCHEDULE_FILE" \
    || BEATDB="/tmp/celerybeat-schedule"

echo "Beat DB: ${BEATDB}"

echo "Environment variables in use:" 
env | grep DM_

celery -A 'app.tasks' worker -l info -B -s "$BEATDB"
