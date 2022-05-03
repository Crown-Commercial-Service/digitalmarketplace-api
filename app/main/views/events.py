import pendulum
import json
from flask import jsonify
from .. import main
from app.api.services import key_values_service


@main.route('/events', methods=['GET'])
def get_events():
    event_values = key_values_service.get_by_key('events')
    events = list()

    if event_values:
        for ev in event_values['data']:
            event = {}
            event['title'] = ev.get('title', '')
            datetime = ev.get('datetime', '')
            event['url'] = ev.get('url', '')
            event['audience'] = ev.get('audience', 'both')
            event['active'] = ev.get('active', False)
            event['completed'] = True
            event['attachments'] = list()
            attachments = ev.get('attachments', None)
            if attachments:
                for file in attachments:
                    attachment = {}
                    attachment['name'] = file.get('name', '')
                    attachment['url'] = file.get('url', '')
                    attachment['type'] = file.get('type', '')
                    attachment['size'] = file.get('size', '')
                    event['attachments'].append(attachment)
                    event['attachments'] = sorted(event['attachments'], key=lambda f: f['name'])

            if event['active'] and datetime:
                try:
                    event['datetime'] = pendulum.parse(datetime)
                    event['datetime_string'] = event['datetime'].format('ddd D MMM YYYY [at] h:mmA')
                    if event['datetime'].date() >= pendulum.now().date():
                        event['completed'] = False
                    events.append(event)
                except pendulum.parsing.exceptions.ParserError:
                    pass

    if len(events) > 0:
        events = sorted(events, key=lambda k: (k['completed'], k['datetime']))

    return jsonify(events)
