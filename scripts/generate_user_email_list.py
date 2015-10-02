"""

Usage:
    scripts/generate-user-email-list.py <data_api_url> <data_api_token> [--framework=<slug>] [--status]
"""
import sys
sys.path.insert(0, '.')

from docopt import docopt
from app.scripts.generate_user_email_list import list_users, list_users_with_status


if __name__ == '__main__':
    arguments = docopt(__doc__)

    if arguments.get('--status'):
        list_users_with_status(
            data_api_url=arguments['<data_api_url>'],
            data_api_token=arguments['<data_api_token>'],
            framework_slug=arguments.get('--framework'))
    else:
        list_users(
            data_api_url=arguments['<data_api_url>'],
            data_api_token=arguments['<data_api_token>'],
            framework_slug=arguments.get('--framework'))
