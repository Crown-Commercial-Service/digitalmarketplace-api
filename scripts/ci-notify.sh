#!/bin/bash

curl -g -X POST --data-urlencode 'payload={"channel": "#marketplace", "username": "releasebot", "text": "A new Api went live! '"$CIRCLE_REPOSITORY_URL"'/releases/tag/'"$CIRCLE_TAG"'", "icon_emoji": ":lightning:"}' "$SLACK_WEBHOOK_URL"