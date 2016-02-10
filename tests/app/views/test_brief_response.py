from ..helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestCreateBriefResponse(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/brief-responses'
    method = 'post'
