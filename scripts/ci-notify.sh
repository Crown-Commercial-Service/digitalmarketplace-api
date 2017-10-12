#!/bin/bash
LASTTAG=$(git describe --abbrev=0 --tags HEAD~1)
GITLOG=$(git log --no-merges --format="%cd %s" --date=short $LASTTAG...HEAD | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\n/g')
PAYLOAD='{"channel": "#marketplace", "icon_emoji": ":lightning:","username": "releasebot",
 "attachments": [ { "fallback": "A new API went live!",
 "pretext": "A new API went live! '"$CIRCLE_REPOSITORY_URL"'/releases/tag/'"$CIRCLE_TAG"'",
 "text": "'"$GITLOG"'" }] }'

echo $PAYLOAD
curl -g -X POST --data-urlencode "payload=$PAYLOAD" "$SLACK_WEBHOOK_URL"

ENVIRONMENT=production
LOCAL_USERNAME=`whoami`
REVISION=`git log -n 1 --pretty=format:"%H"`

curl https://api.rollbar.com/api/1/deploy/ \
  -F access_token=$ROLLBAR_TOKEN \
  -F environment=$ENVIRONMENT \
  -F revision=$REVISION \
  -F local_username=$LOCAL_USERNAME