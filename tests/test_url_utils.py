from app.url_utils import force_relative_url


class TestForceRelativeURL(object):
    def test_hostname_removed(self):
        result = force_relative_url('http://hostname:port/', 'https://badhostname/plus/path?woo')
        assert result == "plus/path?woo"

    def test_additional_base_path_removed(self):
        result = force_relative_url('http://hostname:port/extra/', 'https://badhostname/extra/plus/path?woo')
        assert result == "plus/path?woo"

    def test_additional_base_path_no_slash(self):
        # This is a stupid case: the missing slash means that our relative URL *must* include the 'extra' part,
        # if it is to actually work when eventually re-joined to the base URL. (urljoin will, as expected,
        # remove the resource at the bottom level when joining a relative URL.)
        result = force_relative_url('http://hostname:port/extra', 'https://badhostname/extra/plus/path?woo')
        assert result == "extra/plus/path?woo"

    def test_mismatched_base_paths_ignored(self):
        result = force_relative_url('http://hostname:port/extra/', 'https://badhostname/mismatch/plus/path?woo')
        # No way to be sure that removing "mismatch" is correct - so we must not (if this ever happened we
        # probably did something wrong).
        assert result == "/mismatch/plus/path?woo"
