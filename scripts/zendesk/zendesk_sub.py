from zdesk import Zendesk


class ZendeskSub(Zendesk):
    def channels_voice_stats_account_overview_list(self, **kwargs):
        "https://developer.zendesk.com/rest_api/docs/voice-api/stats#account-overview"
        api_path = "/api/v2/channels/voice/stats/account_overview.json"
        return self.call(api_path, **kwargs)
