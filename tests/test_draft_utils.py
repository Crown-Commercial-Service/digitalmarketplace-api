import mock

from app.draft_utils import get_copiable_service_data


class TestGetCopiableServiceData:

    service_data = mock.Mock()
    service_data.data = {
        "niceField": "nice value",
        "badField": "bad value",
        "neutralField": "neutral value"
    }

    def test_get_copiable_service_data_returns_all_data_by_default(self):
        assert get_copiable_service_data(self.service_data) == {
            "niceField": "nice value",
            "badField": "bad value",
            "neutralField": "neutral value"
        }

    def test_get_copiable_service_data_only_copies_fields_to_copy(self):
        assert get_copiable_service_data(self.service_data, questions_to_copy=['niceField']) == {
            "niceField": "nice value"
        }

    def test_get_copiable_service_data_filters_out_fields_to_exclude(self):
        assert get_copiable_service_data(self.service_data, questions_to_exclude=['badField']) == {
            "niceField": "nice value",
            "neutralField": "neutral value"
        }

    def test_get_copiable_service_data_excludes_fields_if_both_options_supplied(self):
        assert get_copiable_service_data(
            self.service_data,
            questions_to_exclude=['badField'],
            questions_to_copy=['niceField'],
        ) == {
            "niceField": "nice value",
            "neutralField": "neutral value"
        }
