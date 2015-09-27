#!/usr/bin/env python
"""Change user password

Usage:
    chpass.py <user_email> <stage> <api_token> [options]

    --unlock  If set, unlocks user account after changing the password

Example:
    ./chpass.py admin@example.com dev myToken --unlock
"""

import sys
import getpass
import logging

logger = logging.getLogger('chpass')
logging.basicConfig(level=logging.INFO)

from docopt import docopt

from dmutils import apiclient


def get_api_endpoint_from_stage(stage):
    stage_prefixes = {
        'preview': 'preview-api.development',
        'staging': 'staging-api',
        'production': 'api'
    }

    if stage in ['local', 'dev', 'development']:
        return 'http://localhost:5000'

    return "https://{}.digitalmarketplace.service.gov.uk".format(
        stage_prefixes[stage]
    )


def update_user_password(api_endpoint, api_token, user_email, new_password, unlock=False):
    data_client = apiclient.DataAPIClient(api_endpoint, api_token)

    try:
        user = data_client.get_user(email_address=user_email)['users']
        data_client.update_user_password(user['id'], new_password)
        if unlock:
            data_client.update_user(user['id'], locked=False, updater=getpass.getuser())
            logger.info("User unlocked")
    except apiclient.APIError:
        sys.exit(1)

    logger.info("Password updated")


if __name__ == '__main__':
    arguments = docopt(__doc__)

    password = getpass.getpass()

    update_user_password(
        get_api_endpoint_from_stage(arguments['<stage>']),
        arguments['<api_token>'],
        arguments['<user_email>'],
        password,
        arguments['--unlock']
    )
