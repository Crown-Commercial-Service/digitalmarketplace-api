#!/bin/bash
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Already in virtual environment $VIRTUAL_ENV"
else
  source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."
fi

echo "Environment variables in use:" 
env | grep DM_

# Database version pre-flight check
CURRENT_DB_VERSION="$(python application.py db current 2>/dev/null | grep '(head)' | cut -f 1 -d ' ')"
LATEST_DB_VERSION="$(python scripts/list_migrations.py | tail -n 1 | cut -f 1 -d ' ')"
if [ -z "$SKIP_DB_CHECK" ] && [ "$CURRENT_DB_VERSION" -ne "$LATEST_DB_VERSION" ]; then
  >&2 echo -e "\033[1;31mYour database version ($CURRENT_DB_VERSION) is not up to date ($LATEST_DB_VERSION).\033[0m" \
              "\nUpdate it with 'python application.py db upgrade' or skip this check by setting the SKIP_DB_CHECK" \
              "environment variable."
  exit 1
fi

if [ "$1" = "gunicorn" ]; then
  "$VIRTUAL_ENV/bin/pip" install gunicorn
  "$VIRTUAL_ENV/bin/gunicorn" -w 4 -b 127.0.0.1:5000 application:application
else
  python application.py runserver
fi
