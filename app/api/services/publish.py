import json
import boto3


class Publish(object):

    def agency(self, agency, event_type, **kwargs):
        return self.__generic('agency', event_type, agency=agency, **kwargs)

    def application(self, application, event_type, **kwargs):
        return self.__generic('application', event_type, application=application, **kwargs)

    def assessment(self, assessment, event_type, **kwargs):
        return self.__generic('assessment', event_type, assessment=assessment, **kwargs)

    def brief(self, brief, event_type, **kwargs):
        return self.__generic('brief', event_type, brief=brief, **kwargs)

    def brief_response(self, brief_response, event_type, **kwargs):
        return self.__generic('brief_response', event_type, brief_response=brief_response, **kwargs)

    def brief_question(self, brief_question, event_type, **kwargs):
        return self.__generic('brief_question', event_type, brief_question=brief_question, **kwargs)

    def evidence(self, evidence, event_type, **kwargs):
        return self.__generic('evidence', event_type, evidence=evidence, **kwargs)

    def supplier(self, supplier, event_type, **kwargs):
        return self.__generic('supplier', event_type, supplier=supplier, **kwargs)

    def supplier_domain(self, supplier_domain, event_type, **kwargs):
        return self.__generic('supplier_domain', event_type, supplier_domain=supplier_domain, **kwargs)

    def team(self, team, event_type, **kwargs):
        return self.__generic('team', event_type, team=team, **kwargs)

    def user(self, user, event_type, **kwargs):
        return self.__generic('user', event_type, user=user, **kwargs)

    def user_claim(self, user_claim, event_type, **kwargs):
        return self.__generic('user_claim', event_type, user_claim=user_claim, **kwargs)

    def __generic(self, object_type, event_type, **kwargs):
        from . import key_values_service
        key_values = (
            key_values_service
            .convert_to_object(
                key_values_service
                .get_by_keys(
                    'aws_sns'
                )
            )
            .get('aws_sns', None)
        )
        if not key_values:
            return None

        client = boto3.client(
            'sns',
            region_name=key_values.get('aws_sns_region', None),
            aws_access_key_id=key_values.get('aws_sns_access_key_id', None),
            aws_secret_access_key=key_values.get('aws_sns_secret_access_key', None),
            endpoint_url=key_values.get('aws_sns_url', None)
        )

        message = {}
        if kwargs:
            for key, value in kwargs.iteritems():
                message[key] = value

        response = client.publish(
            TopicArn=key_values.get('aws_sns_topicarn', None),
            Message=json.dumps({
                'default': json.dumps(message)
            }),
            MessageStructure='json',
            MessageAttributes={
                'object_type': {
                    'DataType': 'String',
                    'StringValue': object_type
                },
                'event_type': {
                    'DataType': 'String',
                    'StringValue': event_type
                }
            }
        )
        return response
