#!/usr/bin/env python
"""Change user password

Usage:
    snapshot_framework_stats.py <framework_slug> <stage> <api_token>

Example:
    ./snapshot_framework_stats.py g-cloud-7 dev myToken
"""

import sys
import logging

logger = logging.getLogger('script')
logging.basicConfig(level=logging.INFO)

from docopt import docopt

from dmutils import apiclient
from dmutils.audit import AuditTypes


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


def snapshot_framework_stats(api_endpoint, api_token, framework_slug):
    data_client = apiclient.DataAPIClient(api_endpoint, api_token)

    try:
        stats = data_client.get_framework_stats(framework_slug)
        data_client.create_audit_event(
            AuditTypes.snapshot_framework_stats,
            data=stats,
            object_type='frameworks',
            object_id=framework_slug
        )
    except apiclient.APIError:
        sys.exit(1)

    logger.info("Framework stats snapshot saved")


if __name__ == '__main__':
    arguments = docopt(__doc__)

    snapshot_framework_stats(
        get_api_endpoint_from_stage(arguments['<stage>']),
        arguments['<api_token>'],
        arguments['<framework_slug>'],
    )
