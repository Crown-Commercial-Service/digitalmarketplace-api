import pendulum
from utils import Utils


class Reporting(object):
    def __init__(self):
        self.__utils = Utils()

    def ticket(self):
        print 'reporting tickets'
        data = self.__utils.open_json_file('retrieval_ticket_metrics.json')

        ticket_metrics = data.get('ticket_metrics')
        result = {}
        for ticket_metric in ticket_metrics:
            created_at = pendulum.parse(ticket_metric.get('created_at'))
            full_resolution_time_in_minutes = ticket_metric.get('full_resolution_time_in_minutes', None)
            business_minutes = 0
            if full_resolution_time_in_minutes and full_resolution_time_in_minutes.get('business'):
                business_minutes = full_resolution_time_in_minutes['business']

            key = '{}-{}'.format(created_at.year, created_at.month)
            if key not in result:
                result[key] = {
                    'count': 1,
                    'business_minutes': [business_minutes]
                }
            else:
                result[key]['count'] = result[key]['count'] + 1
                result[key]['business_minutes'].append(business_minutes)

        for v in result.itervalues():
            v['median_full_resolution_minutes'] = self.__utils.median(v['business_minutes'])
            v['total_full_resolution_minutes'] = sum(v['business_minutes'])
            del v['business_minutes']

        self.__utils.write_to_file('reporting_ticket.json', result)

    def run(self):
        self.ticket()
