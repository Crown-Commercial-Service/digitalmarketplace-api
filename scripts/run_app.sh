#!/bin/bash
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Already in virtual environment $VIRTUAL_ENV"
else
  source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."
fi

echo "Environment variables in use:" 
env | grep DM_

if [ "$1" = "gunicorn" ]; then
  "$VIRTUAL_ENV/bin/pip" install gunicorn
  "$VIRTUAL_ENV/bin/gunicorn" -w 4 -b 127.0.0.1:5000 application:application
else
  python application.py runserver
fi
