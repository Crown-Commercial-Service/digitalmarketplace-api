#!/bin/bash
source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."

# Use default environment vars for localhost if not already set
export AUTH_TOKENS=${AUTH_TOKENS:=myToken}

echo "Environment variables in use:" 
env | grep AUTH_TOKENS

python application.py runserver
