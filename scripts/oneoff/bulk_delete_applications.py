#!/usr/bin/env python
"""
Usage:
    bulk_delete_applications.py <api_endpoint> <api_access_token>
"""

from docopt import docopt
import dmapiclient


def main(api_url, api_access_token):
    client = dmapiclient.DataAPIClient(api_url, api_access_token)
    for id in [1, 2, 3]:
        print(id)
        try:
            client.req.applications(id).delete(data={"updated_by": ''})
            print("deleted {}".format(id))
        except Exception as e:
            print(e)


if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
    )
