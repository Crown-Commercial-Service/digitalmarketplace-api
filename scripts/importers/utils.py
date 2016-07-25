import urlparse
import requests

def nonEmptyOrNone(s):
    """
    Converts empty strings to None.

    Needed because CSV format doesn't know the difference.
    Used when strings should not be empty, and empty source data means unknown.
    """
    if s:
        return s
    return None


class Response(object):

    def __init__(self, code, data):
        self.status_code = code
        self.data = data

    def get_data(self):
        return self.data


class Client(object):

    def __init__(self, api_host, api_token):
        self.api_host = api_host
        self.headers = {'Authorization': 'Bearer {}'.format(api_token)}

    def get(self, path, data, **kwargs):
        return self.open(method='GET', path=path, data=data, **kwargs)

    def post(self, path, data, **kwargs):
        return self.open(method='POST', path=path, data=data, **kwargs)

    def patch(self, path, data, **kwargs):
        return self.open(method='PATCH', path=path, data=data, **kwargs)

    def open(self, method, path, data, content_type):
        api_url = urlparse.urljoin(self.api_host, path)

        headers = self.headers.copy()
        headers['Content-Type'] = content_type

        if method == 'GET':
            handleRequest = requests.get
        elif method == 'POST':
            handleRequest = requests.post
        elif method == 'PATCH':
            handleRequest = requests.patch
        else:
            raise NotImplementedError(method)

        result = handleRequest(api_url, data=data, headers=headers)
        return Response(result.status_code, result.text)


def makeClient():
    import os
    import sys

    api_token = os.environ.get('DM_DATA_API_AUTH_TOKEN')
    if len(sys.argv) > 1:
        api_host = sys.argv[1]
    else:
        api_host = 'http://localhost:5000/'

    return Client(api_host, api_token)
