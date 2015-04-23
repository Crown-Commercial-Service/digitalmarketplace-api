#!/bin/bash
source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."

# Use default environment vars for localhost if not already set
export DM_API_AUTH_TOKENS=${DM_API_AUTH_TOKENS:=myToken}
export DM_SEARCH_API_AUTH_TOKEN=${DM_SEARCH_API_AUTH_TOKEN:=myToken}
export DM_SEARCH_API_URL=${DM_SEARCH_API_URL:=http://localhost:5001}

echo "Environment variables in use:" 
env | grep DM_

python application.py runserver
