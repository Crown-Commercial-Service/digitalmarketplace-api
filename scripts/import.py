#!/usr/bin/env python
import sys
import json
import os
import requests
import multiprocessing


def list_files(directory):
    for root, subdirs, files in os.walk(directory):
        print("ROOT: {}".format(root))
        for file in files:
            yield os.path.abspath(os.path.join(root, file))

        for subdir in subdirs:
            for subfile in list_files(subdir):
                yield subfile


if __name__ == "__main__":
    _, base_url, access_token, listing_dir = sys.argv

    endpoint = "{}/services".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Listing dir: {}".format(listing_dir))

    def put_file(file_path):
        with open(file_path) as f:
            data = json.load(f)
            data = {'services': data}
            url = '{}/{}'.format(endpoint, data['services']['id'])
            response = requests.put(
                url,
                data=json.dumps(data),
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer {}".format(access_token),
                })
            return response

    pool = multiprocessing.Pool(10)

    for result in pool.imap(put_file, list_files(listing_dir)):
        print(result)
