import json
import os


class Utils(object):
    def __init__(self):
        self.__ZENDESK_OUTPUT_PATH = os.path.expanduser("~")
        if 'ZENDESK_OUTPUT_PATH' in os.environ:
            self.__ZENDESK_OUTPUT_PATH = os.environ['ZENDESK_OUTPUT_PATH']

        print 'ZENDESK_OUTPUT_PATH: {}'.format(self.__ZENDESK_OUTPUT_PATH)

    def median(self, lst):
        n = len(lst)
        if n < 1:
                return None
        if n % 2 == 1:
                return sorted(lst)[n // 2]
        else:
                return sum(sorted(lst)[n // 2 - 1:n // 2 + 1]) / 2.0

    def open_json_file(self, filename):
        path = os.path.join(self.__ZENDESK_OUTPUT_PATH, 'zendesk', filename)
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    def write_to_file(self, filename, content):
        path = os.path.join(self.__ZENDESK_OUTPUT_PATH, 'zendesk')
        if os.path.exists(path) is False:
            os.mkdir(path)
        with open(os.path.join(path, filename), 'w') as file:
            file.write(json.dumps(content, sort_keys=True, indent=4))
