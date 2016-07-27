#!/bin/sh
cf target -o dto -s digital-marketplace
cf push -c 'python application.py db upgrade' -u 'none'
cf push
