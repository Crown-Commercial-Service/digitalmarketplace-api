#!/bin/bash
source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."

# Use default environment vars for localhost if not already set
export DM_API_AUTH_TOKENS=${DM_API_AUTH_TOKENS:=myToken}

echo "Environment variables in use:" 
env | grep DM_

python application.py runserver
