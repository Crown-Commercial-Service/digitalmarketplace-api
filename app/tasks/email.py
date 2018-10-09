from __future__ import \
    unicode_literals, \
    absolute_import

from . import celery
import boto3
import botocore.exceptions
import textwrap
import sys
from flask import current_app
from flask._compat import string_types
from dmutils.email import hash_email, to_bytes, to_text, EmailError
from string import Template
from os import getenv


@celery.task
def send_email(to_email_addresses, email_body, subject, from_email, from_name, reply_to=None):
    if isinstance(to_email_addresses, string_types):
        to_email_addresses = [to_email_addresses]

    if current_app.config.get('DM_SEND_EMAIL_TO_STDERR', False):
        email_body = to_text(email_body)
        subject = to_text(subject)

        template = Template(textwrap.dedent("""\
            To: $to
            Subject: $subject
            From: $from_line
            Reply-To: $reply_to

            $body"""))

        subbed = template.substitute(
            to=', '.join(to_email_addresses),
            subject=subject,
            from_line='{} <{}>'.format(from_name, from_email),
            reply_to=reply_to,
            body=email_body
        )
        sys.stderr.write(subbed)
    else:
        try:
            email_body = to_bytes(email_body)
            subject = to_bytes(subject)

            email_client = boto3.client(
                'ses',
                region_name=getenv('AWS_REGION'),
                aws_access_key_id=getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=getenv('AWS_SECRET_ACCESS_KEY')
            )

            destination_addresses = {
                'ToAddresses': to_email_addresses,
            }
            if 'DM_EMAIL_BCC_ADDRESS' in current_app.config:
                destination_addresses['BccAddresses'] = [current_app.config['DM_EMAIL_BCC_ADDRESS']]

            return_address = current_app.config.get('DM_EMAIL_RETURN_ADDRESS')

            result = email_client.send_email(
                Source=u"{} <{}>".format(from_name, from_email),
                Destination=destination_addresses,
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': email_body,
                            'Charset': 'UTF-8'
                        }
                    }
                },
                ReturnPath=return_address or reply_to or from_email,
                ReplyToAddresses=[reply_to or from_email],
            )

            current_app.logger.info("Sent email: id={id}, email={email_hash}",
                                    extra={
                                        'id': result['ResponseMetadata']['RequestId'],
                                        'email_hash': hash_email(to_email_addresses[0])
                                    })

        except botocore.exceptions.ClientError as e:
            current_app.logger.error(
                "An SES error occurred: %s, when sending to %s",
                e.response['Error']['Message'],
                (' & ').join(to_email_addresses)
            )
            raise EmailError(e.response['Error']['Message'])
