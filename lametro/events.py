import datetime
import io
import logging

import pdfplumber
import pytesseract
import requests
from legistar.events import LegistarAPIEventScraper
from Levenshtein import distance
from pdfminer.pdfparser import PDFSyntaxError
from PIL import Image
from pupa.scrape import Event, Scraper
from sentry_sdk import capture_exception, capture_message

from .paired_event_stream import PairedEventStream

TOKEN: str | None = None
try:
    from .secrets import TOKEN
except ImportError:
    pass


LOGGER = logging.getLogger(__name__)


class DuplicateAgendaItemException(Exception):
    def __init__(self, event, legistar_api_url):
        message = (
            "An agenda has duplicate agenda items on the Legistar grid: "
            f"{event.name} on {event.start_date.strftime('%B %d, %Y')} "
            f"({legistar_api_url}). Contact Metro, and ask them to remove the "
            "duplicate EventItemAgendaSequence."
        )

        super().__init__(message)


class MissingAttachmentsException(Exception):
    def __init__(self, matter_id, attachment_url):
        message = (
            f"No attachments for the approved minutes matter with an ID of {matter_id}. "
            f"View the list of available attachments at <{attachment_url}>. "
            "Contact Metro, and ask them to confirm whether this should have an attachment."
        )

        super().__init__(message)


class LametroEventScraper(LegistarAPIEventScraper, Scraper):
    BASE_URL = "https://webapi.legistar.com/v1/metro"
    WEB_URL = "https://metro.legistar.com/"
    EVENTSPAGE = "https://metro.legistar.com/Calendar.aspx"
    TIMEZONE = "America/Los_Angeles"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if TOKEN:
            self.params = {"token": TOKEN}

    def scrape(self, window=None, event_ids=None):
        if window and event_ids:
            raise ValueError("Can't specify both window and event_ids")

        if event_ids:
            events = (
                self.get(f"{self.BASE_URL}/events/{id}").json()
                for id in event_ids.split(",")
            )

        else:
            n_days_ago = None

            if window and float(window) != 0:
                n_days_ago = datetime.datetime.utcnow() - datetime.timedelta(
                    float(window)
                )

            events = self.api_events(since_datetime=n_days_ago)

        public_events = filter(
            lambda e: e.get("EventInSiteURL")
            and self.head(e["EventInSiteURL"]).status_code == 200
        )

        service_councils = set(
            sc["BodyId"]
            for sc in self.search(
                "/bodies/", "BodyId", "BodyTypeId eq 70 or BodyTypeId eq 75"
            )
        )

        for event, web_event in PairedEventStream(
            public_events, find_missing_partner=True
        ):
            body_name = event["EventBodyName"]

            if "Board of Directors -" in body_name:
                body_name, event_name = [part.strip() for part in body_name.split("-")]
            elif event["EventBodyId"] in service_councils:
                # Don't scrape service council or service council public hearing events.
                self.info(
                    "Skipping event {0} for {1}".format(
                        event["EventId"], event["EventBodyName"]
                    )
                )
                continue
            else:
                event_name = body_name

            # Events can have an EventAgendaStatusName of "Final", "Final Revised",
            # and "Final 2nd Revised."
            # We classify these events as "passed."
            status_name = event["EventAgendaStatusName"]
            if status_name.startswith("Final"):
                status = "passed"
            elif status_name == "Draft":
                status = "confirmed"
            elif status_name == "Canceled":
                status = "cancelled"
            else:
                status = "tentative"

            location = event["EventLocation"]

            if not location:
                # We expect some events to have no location. LA Metro would
                # like these displayed in the Councilmatic interface. However,
                # OCD requires a value for this field. Add a sane default.
                location = "Not available"

            e = Event(
                event_name,
                start_date=event["start"],
                description="",
                location_name=location,
                status=status,
            )

            e.pupa_id = str(event["EventId"])

            # Metro requires the EventGuid to build out MediaPlayer links.
            # Add both the English event GUID, and the Spanish event GUID if
            # it exists, to the extras dict.
            e.extras = {"guid": event["EventGuid"]}

            legistar_api_url = self.BASE_URL + "/events/{0}".format(event["EventId"])
            e.add_source(legistar_api_url, note="api")

            if event.get("SAPEventGuid"):
                LOGGER.info(
                    f"Found SAP event for {event['EventBodyName']} on {event['EventDate']}"
                )
                e.extras["sap_guid"] = event["SAPEventGuid"]

            if web_event.has_ecomment:
                self.info(
                    "Adding eComment link {0} from {1}".format(
                        web_event["eComment"], web_event["Meeting Details"]["url"]
                    )
                )
                e.extras["ecomment"] = web_event["eComment"]

            if "event_details" in event:
                # if there is not a meeting detail page on legistar
                # don't capture the agenda data from the API
                for item in self.agenda(event):
                    agenda_item = e.add_agenda_item(item["EventItemTitle"])
                    if item["EventItemMatterFile"]:
                        identifier = item["EventItemMatterFile"]
                        agenda_item.add_bill(identifier)

                    if item["EventItemAgendaNumber"]:
                        # To the notes field, add the item number as given in the agenda minutes
                        agenda_number = item["EventItemAgendaNumber"]
                        note = "Agenda number, {}".format(agenda_number)
                        agenda_item["notes"].append(note)

                        agenda_item["extras"]["agenda_number"] = agenda_number

                    # The EventItemAgendaSequence provides
                    # the line number of the Legistar agenda grid.
                    agenda_item["extras"]["item_agenda_sequence"] = item[
                        "EventItemAgendaSequence"
                    ]

                # Historically, the Legistar system has duplicated the EventItemAgendaSequence,
                # resulting in data inaccuracies. In such cases, we'll log the event
                # and notify Metro that their data needs to be cleaned (rather than failing).
                try:
                    item_agenda_sequences = [
                        item["extras"]["item_agenda_sequence"] for item in e.agenda
                    ]
                    if len(item_agenda_sequences) != len(set(item_agenda_sequences)):
                        raise DuplicateAgendaItemException(e, legistar_api_url)
                except DuplicateAgendaItemException as exc:
                    capture_exception(exc)

            e.add_participant(name=body_name, type="organization")

            if event.get("SAPEventId"):
                e.add_source(
                    self.BASE_URL + "/events/{0}".format(event["SAPEventId"]),
                    note="api (sap)",
                )

            if event["EventAgendaFile"]:
                e.add_document(
                    note="Agenda",
                    url=event["EventAgendaFile"],
                    media_type="application/pdf",
                    date=self.to_utc_timestamp(
                        event["EventAgendaLastPublishedUTC"]
                    ).date(),
                )

            # in case this event's minutes haven't been approved yet
            e.extras["approved_minutes"] = False

            if event["EventMinutesFile"]:
                e.add_document(
                    note="Minutes",
                    url=event["EventMinutesFile"],
                    media_type="application/pdf",
                    date=self.to_utc_timestamp(
                        event["EventMinutesLastPublishedUTC"]
                    ).date(),
                )
            elif web_event["Published minutes"] != "Not\xa0available":
                e.add_document(
                    note=web_event["Published minutes"]["label"],
                    url=web_event["Published minutes"]["url"],
                    media_type="application/pdf",
                )
            else:
                approved_minutes = self.find_approved_minutes(event)
                for minutes in approved_minutes:
                    e.add_document(
                        note=minutes["MatterAttachmentName"],
                        url=minutes["MatterAttachmentHyperlink"],
                        media_type="application/pdf",
                        date=self.to_utc_timestamp(
                            minutes["MatterAttachmentLastModifiedUtc"]
                        ).date(),
                    )
                    e.extras["approved_minutes"] = True

            for audio in event["audio"]:
                try:
                    redirect_url = self.head(audio["url"]).headers["Location"]

                except KeyError:
                    # In some cases, the redirect URL does not yet
                    # contain the location of the audio file. Skip
                    # these events, and retry on next scrape.
                    continue

                # Sometimes if there is an issue getting the Spanish
                # audio created, Metro has the Spanish Audio link
                # go to the English Audio.
                #
                # Pupa does not allow the for duplicate media links,
                # so we'll ignore the the second media link if it's
                # the same as the first media link.
                #
                # Because of the way that the event['audio'] is created
                # the first audio link is always English and the
                # second is always Spanish
                e.add_media_link(
                    note=audio["label"],
                    url=redirect_url,
                    media_type="text/html",
                    on_duplicate="ignore",
                )

            if event["event_details"]:
                for link in event["event_details"]:
                    e.add_source(**link)
            else:
                e.add_source("https://metro.legistar.com/Calendar.aspx", note="web")

            yield e

    def _suppress_item_matter(self, item, agenda_url):
        """
        Agenda items in Legistar do not always display links to
        associated matter files even if the same agenda item
        in the API references a Matter File. The agenda items
        we scrape should honor the suppression on the Legistar
        agendas.

        This is also practical because matter files that are hidden
        in the Legistar Agenda do not seem to available for scraping
        on Legistar or through the API
        """

        if item["EventItemMatterFile"] is not None:
            if item["EventItemMatterStatus"] == "Draft":
                suppress = True
            elif item["EventItemMatterType"] == "Closed Session":
                suppress = True
            else:
                suppress = False

            if suppress:
                item["EventItemMatterFile"] = None

    def find_approved_minutes(self, event):
        """
        The minutes of some meetings are available as a legislative item
        that are approved at the subsequent meeting. This method tries
        to find them.

        This method is pretty complicated, but if we can get it right
        here, it avoids many complicated and expensive queries in the
        councilmatic app.

        """
        name = event["EventBodyName"]

        if name not in {"Board of Directors - Regular Board Meeting", "LA SAFE"}:
            return None

        # if the event is in the future, there won't have been a chance to
        # approve the minutes
        if event["start"] > datetime.datetime.now(datetime.timezone.utc):
            return None

        date = event["start"].strftime("%B %-d, %Y")

        associated_with_meeting_body = f"MatterBodyId eq {event['EventBodyId']}"
        meeting_date_in_title = f"substringof('{date}', MatterTitle)"
        matter_type_minutes = "MatterTypeName eq 'Minutes'"
        minutes_in_title = "substringof('Minutes', MatterTitle)"
        matter_type_informational = "MatterTypeName eq 'Informational Report'"

        result = self.search(
            "/matters/",
            "MatterId",
            (
                f"{associated_with_meeting_body} and "
                + f"{meeting_date_in_title} and "
                + "("
                + f"({matter_type_minutes}) or "
                + f"({minutes_in_title} and {matter_type_informational})"
                + ")"
            ),
        )

        # Will print a warning if no minutes have been found
        n_minutes = 0

        # Sometimes, the search returns more than one board report.
        # Go through each matter yielded from this generator to account for that.
        for matter in result:
            if (
                matter["MatterRestrictViewViaWeb"]
                or matter["MatterStatusName"] == "Draft"
                or matter["MatterBodyName"] == "TO BE REMOVED"
            ):
                # Ignore this matter if there are signs that it shouldn't be processed.
                continue

            attachment_url = self.BASE_URL + "/matters/{}/attachments".format(
                matter["MatterId"]
            )

            attachments = self.get(attachment_url).json()

            try:
                if len(attachments) == 0:
                    raise MissingAttachmentsException(
                        matter["MatterId"], attachment_url
                    )
            except MissingAttachmentsException as e:
                capture_exception(e)
                continue

            if len(attachments) == 1:
                yield attachments[0]
                n_minutes += 1
            else:
                """
                Multiple attachments have been found.
                Return only those that look like minutes files.
                """
                for attach in attachments:
                    url = attach["MatterAttachmentHyperlink"]
                    response = requests.get(url)

                    with io.BytesIO(response.content) as filestream:
                        try:
                            pdf = pdfplumber.open(filestream)
                        except PDFSyntaxError as e:
                            capture_message(
                                f"PDFPlumber encountered an error opening a file: {e}",
                                "warning",
                            )
                            continue
                        cover_page = pdf.pages[0]

                        cover_page_text = cover_page.extract_text()
                        if not cover_page_text:
                            # No extractable text found.
                            # Turn the page into an image and use OCR to get text.
                            cover_page_image = cover_page.to_image(resolution=300)

                            with io.BytesIO() as in_mem_image:
                                cover_page_image.save(in_mem_image)
                                in_mem_image.seek(0)
                                cover_page_text = pytesseract.image_to_string(
                                    Image.open(in_mem_image)
                                )

                            def edit_distance_lte_n(target, corpus, n):
                                for line in corpus.splitlines():
                                    _distance = distance(target, line, score_cutoff=n)
                                    self.debug(f"{target}, {line}, {_distance}")
                                    if _distance <= n:
                                        self.debug("FOUND MATCH")
                                        return True
                                else:
                                    return False

                            contains_minutes = "minutes" in cover_page_text.lower()
                            contains_exact_body = (
                                name.lower() in cover_page_text.lower()
                            )
                            contains_fuzzy_body = edit_distance_lte_n(
                                name.lower(), cover_page_text.lower(), 2
                            )

                            if contains_minutes and (
                                contains_exact_body or contains_fuzzy_body
                            ):
                                if contains_fuzzy_body:
                                    self.info(
                                        "Found minutes for the {0} meeting of {1} by fuzzy match: {2}".format(
                                            name, date, attach
                                        )
                                    )
                                yield attach
                                n_minutes += 1
                                break

        if n_minutes == 0:
            self.warning(f"Couldn't find minutes for the {name} meeting of {date}.")
