#!/bin/bash
LASTTAG=$(git describe --abbrev=0 --tags HEAD~1)
GITLOG=$(git log --no-merges --format="%cd %s" --date=short $LASTTAG...HEAD | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\n/g' | sed 's/\"/\\"/g')
PAYLOAD='{"channel": "#marketplace", "icon_emoji": ":lightning:","username": "releasebot",
 "attachments": [ { "fallback": ":rotating_light: API is ready to go live!",
 "pretext": ":rotating_light: API is ready to go live! '"$CIRCLE_REPOSITORY_URL"'/releases/tag/'"$CIRCLE_TAG"'",
 "text": "'"$GITLOG"'" }] }'

echo $PAYLOAD
curl -g -X POST --data-urlencode "payload=$PAYLOAD" "$SLACK_MARKETPLACE_SUPPORT_WEBHOOK_URL"

ENVIRONMENT=production
LOCAL_USERNAME=`whoami`
REVISION=`git log -n 1 --pretty=format:"%H"`
