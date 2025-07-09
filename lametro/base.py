import logging
import os

from legistar.events import LegistarAPIEventScraper, WebCalendarMixin
from scrapelib import Scraper

try:
    from .secrets import TOKEN
except ImportError:
    TOKEN = os.getenv("LEGISTAR_API_TOKEN", "")


LOGGER = logging.getLogger(__name__)


class LAMetroAPIWebEventScraper(WebCalendarMixin, LegistarAPIEventScraper, Scraper):
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
    
    def _get_web_event(self, api_event):
        """
        Detail pages for Metro events are not available until agendas are
        finalized. Prior to agendas being finalized, consult the web calendar
        to confirm the meeting is public so we can scrape it before its
        detail page becomes available.
        """
        if self._not_in_web_interface(api_event):
            LOGGER.debug(f"Skipping web check for {api_event}")
            return None
        
        if self._detail_page_not_available(api_event):
            LOGGER.debug(f"Checking web calendar for {api_event}")
            return self.web_results(api_event)

        LOGGER.debug(f"Checking detail link for {api_event}")
        return self.web_detail(api_event)
