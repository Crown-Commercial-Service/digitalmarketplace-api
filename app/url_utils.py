from urllib.parse import urlsplit, urlunsplit


def force_relative_url(base_url, url):
    """
    Forcibly removes the hostname and port from a URL, returning a new URL relative to base_url.
    :param base_url: the path segment of base_url will be used to shorten the return url if possible
    :param url: the URL to process into a relative URL
    :return: sanitised URL relative to base_url
    """
    # convert args to str; urllib can accept bytes but our string ops can't
    base_url, url = str(base_url), str(url)

    # remove the netloc and port from the url...
    parsed_url = urlsplit(url)
    sanitised_url = urlunsplit(('', '', parsed_url.path, parsed_url.query, parsed_url.fragment))

    # ...and remove any common path prefix up to and including the final slash
    base_path = urlsplit(base_url).path or '/'
    base_path = base_path[:base_path.rfind('/') + 1]
    if sanitised_url.startswith(base_path):
        sanitised_url = sanitised_url[len(base_path):]

    return sanitised_url
