import os


def get_version_label():
    try:
        path = os.path.join(os.path.dirname(__file__),
                            '..', '..', 'version_label')
        with open(path) as f:
            return f.read().strip()
    except IOError:
        return None
