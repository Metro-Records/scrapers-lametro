import os

from legistar.events import LegistarAPIEventScraper, WebCalendarMixin
from scrapelib import Scraper

try:
    from .secrets import TOKEN
except ImportError:
    TOKEN = os.getenv("LEGISTAR_API_TOKEN", "")
    

class LAMetroAPIWebEventScraper(WebCalendarMixin, LegistarAPIEventScraper, Scraper):
    BASE_URL = "https://webapi.legistar.com/v1/metro"
    WEB_URL = "https://metro.legistar.com/"
    EVENTSPAGE = "https://metro.legistar.com/Calendar.aspx"
    TIMEZONE = "America/Los_Angeles"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if TOKEN:
            self.params = {"token": TOKEN}

    def _not_in_web_interface(self, api_event):
        return api_event["EventAgendaStatusName"] != "Final"
