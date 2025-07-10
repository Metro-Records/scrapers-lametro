import datetime
import logging
from typing import Generator, Optional

from .base import LAMetroAPIWebEventScraper

LOGGER = logging.getLogger(__name__)


class LAMetroAPIEvent(dict):
    """
    This class is for adding methods to the API event dict
    to faciliate maching events with their other-language
    partners.
    """

    @property
    def is_spanish(self):
        return self["EventBodyName"].endswith(" (SAP)")

    @property
    def own_key(self):
        return (self["EventBodyName"], self["EventDate"])

    @property
    def _partner_name(self):
        if self.is_spanish:
            return self["EventBodyName"].rstrip(" (SAP)")
        else:
            return self["EventBodyName"] + " (SAP)"

    def is_partner(self, other):
        return (
            self._partner_name == other["EventBodyName"]
            and self["EventDate"] == other["EventDate"]
        )

    @property
    def partner_search_string(self):
        search_string = "EventBodyName eq '{}'".format(self._partner_name)
        search_string += " and EventDate eq datetime'{}'".format(self["EventDate"])

        return search_string

    @property
    def partner_key(self):
        return (self._partner_name, self["EventDate"])

    @property
    def key(self):
        return (self["EventBodyName"], self["EventDate"])


def LAMetroWebEvent(event_dict):
    if "Meeting video" in event_dict:
        return LAMetroWebEventDetail(event_dict)
    else:
        return LAMetroWebCalendarEvent(event_dict)


class LAMetroWebEventDetail(dict):
    """
    This class is for adding methods to the web event dict
    to facilitate labeling and sourcing audio appropriately.
    """
    AUDIO_KEY = "Meeting video"
    ECOMMENT_KEY = "eComment"

    @property
    def has_web_link(self):
        return isinstance(self["Meeting Details"], dict)

    @property
    def has_audio(self):
        return self[self.AUDIO_KEY] != "Not\xa0available"

    @property
    def has_ecomment(self):
        return self[self.ECOMMENT_KEY] != "Not\xa0available"


class LAMetroWebCalendarEvent(LAMetroWebEventDetail):
    AUDIO_KEY = "Audio"


class PairedEventStream:
    """
    - Input: Stream of events that need to be paired
        - Deduplicate events
        - Pair events
            - From stream
            - From API (partner search)
        - Merge events
    - Output: Stream of events that have been merged
    """

    def __init__(self, events: list[dict], find_missing_partner: bool = True) -> None:
        self.events = [LAMetroAPIEvent(event) for event in events]
        self.find_missing_partner = find_missing_partner

    def __iter__(
        self,
    ) -> Generator[tuple[LAMetroAPIEvent, LAMetroWebEventDetail | LAMetroWebCalendarEvent], None, None]:
        for event, web_event in self.merged_events:
            yield LAMetroAPIEvent(event), LAMetroWebEvent(web_event)

    @property
    def scraper(self):
        if not hasattr(self, "_scraper"):
            scraper = LAMetroAPIWebEventScraper()
            scraper.retry_attempts = 3
            scraper.requests_per_minute = 0
            self._scraper = scraper
        return self._scraper

    @property
    def unique_events(self) -> Generator[LAMetroAPIEvent, None, None]:
        last_key = None

        for event in sorted(self.events, key=lambda e: e.own_key):
            if event.own_key == last_key:
                raise ValueError(
                    f"Found duplicate event key '{event.own_key}'. Skipping the following event...\n{event}."
                )

            yield event
            last_key = event.own_key

    @property
    def paired_events(
        self,
    ) -> Generator[tuple[LAMetroAPIEvent, Optional[LAMetroAPIEvent]], None, None]:
        unpaired_events: dict[tuple[str, str], LAMetroAPIEvent] = {}

        for event in self.unique_events:
            try:
                partner_event: LAMetroAPIEvent = unpaired_events[event.partner_key]
            except KeyError:
                unpaired_events[event.key] = event
            else:
                del unpaired_events[event.partner_key]
                english_event, spanish_event = sorted(
                    [event, partner_event], key=lambda e: e.is_spanish
                )
                yield english_event, spanish_event

        for event in unpaired_events.values():
            found_partner: Optional[LAMetroAPIEvent] = (
                self.find_partner(event) if self.find_missing_partner else None
            )

            if found_partner:
                english_event, spanish_event = sorted(
                    [event, found_partner], key=lambda e: e.is_spanish
                )
                yield english_event, spanish_event
            elif event.is_spanish:
                spanish_start_date = datetime.datetime(2018, 5, 15, 0, 0, 0, 0)
                event_date = datetime.datetime.strptime(
                    event["EventDate"], "%Y-%m-%dT%H:%M:%S"
                )

                if event_date > spanish_start_date and event.is_spanish:
                    raise ValueError(
                        f"Could not find English partner for Spanish event:\n{event}"
                    )
            else:
                yield (event, None)

    @property
    def merged_events(self) -> Generator[tuple[dict, dict], None, None]:
        for english_event, spanish_event in self.paired_events:
            event_details = []
            event_audio = []
            try:
                event, web_event = self.scraper.event(english_event)
            except (ValueError, TypeError) as e:
                LOGGER.warning(
                    f"English event discarded by base scraper due to the following error: {e}"
                )
                continue
            
            en_web_event = LAMetroWebEvent(web_event)
                        
            if en_web_event.has_web_link:
                event_details.append(
                    {
                        "url": web_event["Meeting Details"]["url"],
                        "note": "web",
                    }
                )

            if en_web_event.has_audio:
                event_audio.append(web_event[en_web_event.AUDIO_KEY])

            if spanish_event:
                try:
                    partner, partner_web_event = self.scraper.event(spanish_event)
                except (ValueError, TypeError):
                    LOGGER.warning(
                        "Spanish event discarded by base scraper. Skipping merge..."
                    )
                else:
                    event["SAPEventId"] = partner["EventId"]
                    event["SAPEventGuid"] = partner["EventGuid"]
                    
                    sap_web_event = LAMetroWebEvent(partner_web_event)
                    
                    if sap_web_event.has_web_link:
                        event_details.append(
                            {
                                "url": partner_web_event["Meeting Details"]["url"],
                                "note": "web (sap)",
                            }
                        )

                    if sap_web_event.has_audio:
                        partner_web_event[sap_web_event.AUDIO_KEY]["label"] = "Audio (SAP)"
                        event_audio.append(partner_web_event[sap_web_event.AUDIO_KEY])

            event.update(
                {
                    "event_details": event_details,
                    "audio": event_audio,
                }
            )

            yield event, web_event

    def find_partner(self, event: LAMetroAPIEvent) -> Optional[LAMetroAPIEvent]:
        """
        Attempt to find other-language partner of an
        event. Sometimes English events won't have Spanish
        partners, but every Spanish event should have an
        English partner.
        """
        results = list(
            self.scraper.search("/events/", "EventId", event.partner_search_string)
        )

        if results:
            (partner,) = results
            partner = LAMetroAPIEvent(partner)
            assert event.is_partner(partner)
            return partner

        return None
