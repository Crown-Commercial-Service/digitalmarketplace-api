#!/usr/bin/env python
from __future__ import print_function
import sys
import json
import os
import requests
import multiprocessing
from datetime import datetime


def list_files(directory):
    for root, subdirs, files in os.walk(directory):
        print("ROOT: {}".format(root))
        for filename in files:
            yield os.path.abspath(os.path.join(root, filename))

        for subdir in subdirs:
            for subfile in list_files(subdir):
                yield subfile


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.now() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta))


def file_putter(endpoint, access_token):

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
            return file_path, response

    return put_file


def do_import(base_url, access_token, listing_dir):
    endpoint = "{}/services".format(base_url)
    put_file = file_putter(endpoint, access_token)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Listing dir: {}".format(listing_dir))

    pool = multiprocessing.Pool(10)

    counter = 0
    start_time = datetime.now()
    for file_path, response in pool.imap(put_file, list_files(listing_dir)):
        if response.status_code / 100 != 2:
            print("ERROR: {} on {}".format(response.status_code, file_path),
                  file=sys.stderr)
        else:
            counter += 1
            print_progress(counter, start_time)

    print_progress(counter, start_time)

if __name__ == "__main__":
    do_import(*sys.argv[1:])
