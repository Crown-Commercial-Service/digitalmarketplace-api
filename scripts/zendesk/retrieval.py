import os
from utils import Utils
from zendesk_sub import ZendeskSub
from zdesk import ZendeskError


class Retrieval(object):
    def __init__(self):
        zendesk_url = os.environ['ZENDESK_URL']
        zendesk_username = os.environ['ZENDESK_USERNAME']
        zendeks_token = os.environ['ZENDESK_TOKEN']

        print 'ZENDESK_URL: {}'.format(zendesk_url)
        print 'ZENDESK_USERNAME: {}'.format(zendesk_username)
        print 'ZENDESK_TOKEN: {}'.format(zendeks_token)
        self.__zendesk = ZendeskSub(zendesk_url, zendesk_username, zendeks_token, True)
        self.__utils = Utils()

    def tickets(self):
        print 'retrieving tickets'
        ticket_metrics = self.__zendesk.tickets_list(get_all_pages=True)
        self.__utils.write_to_file('retrieval_tickets.json', ticket_metrics)

    def ticket_fields(self):
        print 'retrieving tickets fields'
        ticket_fields = self.__zendesk.ticket_fields_list(get_all_pages=True)
        self.__utils.write_to_file('retrieval_ticket_fields.json', ticket_fields)

    def ticket_metrics(self):
        print 'retrieving tickets metrics'
        ticket_metrics = self.__zendesk.ticket_metrics_list(get_all_pages=True)
        self.__utils.write_to_file('retrieval_ticket_metrics.json', ticket_metrics)

    def voice_stats_account_overview(self):
        print 'retrieving voice stats account overview'
        try:
            account_overview = self.__zendesk.channels_voice_stats_account_overview_list()
            self.__utils.write_to_file('retrieval_account_overview.json', account_overview)
        except ZendeskError:
            print 'ERROR while retrieving voice stats account overview'
            pass

    def run(self):
        self.tickets()
        self.ticket_fields()
        self.ticket_metrics()
        self.voice_stats_account_overview()
