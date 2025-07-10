from dateutil import parser
import logging
import os
import pytz

from legistar.events import LegistarAPIEventScraper, WebCalendarFallbackMixin
from scrapelib import Scraper

try:
    from .secrets import TOKEN
except ImportError:
    TOKEN = os.getenv("LEGISTAR_API_TOKEN", "")


LOGGER = logging.getLogger(__name__)


class LAMetroAPIWebEventScraper(WebCalendarFallbackMixin, LegistarAPIEventScraper, Scraper):
    BASE_URL = "https://webapi.legistar.com/v1/metro"
    WEB_URL = "https://metro.legistar.com/"
    EVENTSPAGE = "https://metro.legistar.com/Calendar.aspx"
    TIMEZONE = "America/Los_Angeles"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if TOKEN:
            self.params = {"token": TOKEN}
            
    def _detail_page_not_available(self, api_event):
        return api_event["EventAgendaStatusName"] == "Draft"

    def _not_in_web_interface(self, api_event):
        return api_event["EventBodyName"] == "OCEO Draft Review"
    
    def _event_key(self, event):
        """
        The base scraper parses the event time from the related calendar
        event, but issues a request to every single one, which takes a
        really long time. Parse the date and time from the event instead.
        """
        event_time = pytz.timezone(self.TIMEZONE).localize(
            parser.parse(
                f"{event['Meeting Date']} {event['Meeting Time']}", 
                fuzzy=True
            )
        )

        key = (event['Name']['label'], event_time)

        return key
