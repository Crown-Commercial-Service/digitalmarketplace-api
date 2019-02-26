#!/bin/bash
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Already in virtual environment $VIRTUAL_ENV"
else
  source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."
fi


echo "Setup Localstack"
aws --endpoint-url=http://localhost:4572 s3 mb s3://dta-digital-marketplace-local
aws --endpoint-url=http://localhost:4576 sqs create-queue --queue-name dta-marketplace-local
aws --endpoint-url=http://localhost:4576 sqs create-queue --queue-name dta-marketplace-local-slack
aws --endpoint-url=http://localhost:4575 sns create-topic --name dta-marketplace-local
aws --endpoint-url=http://localhost:4575 sns subscribe --topic-arn arn:aws:sns:ap-southeast-2:123456789012:dta-marketplace-local --protocol sqs --notification-endpoint http://localhost:4576/queue/dta-marketplace-local-slack
aws --endpoint-url=http://localhost:4579 ses verify-email-identity --email-address marketplace@digital.gov.au
aws --endpoint-url=http://localhost:4579 ses verify-email-identity --email-address no-reply@marketplace.digital.gov.au
aws --endpoint-url=http://localhost:4579 ses verify-email-identity --email-address "Digital Marketplace <no-reply@marketplace.digital.gov.au>"
aws --endpoint-url=http://localhost:4579 ses verify-email-identity --email-address "Digital Marketplace Admin <no-reply@marketplace.digital.gov.au>"
aws --endpoint-url=http://localhost:4579 ses verify-email-identity --email-address "Digital Marketplace Supplier <no-reply@marketplace.digital.gov.au>"


[[ "$CELERY_BEAT_SCHEDULE_FILE" ]] \
    && BEATDB="$CELERY_BEAT_SCHEDULE_FILE" \
    || BEATDB="/tmp/celerybeat-schedule"

echo "Beat DB: ${BEATDB}"

echo "Environment variables in use:"
env | grep DM_

celery -A 'app.tasks' worker -l info -B -s "$BEATDB"
