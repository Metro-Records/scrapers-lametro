import json
import re
from io import BytesIO
from pathlib import Path

import pytest
import requests_mock

from lametro.base import LAMetroAPIWebEventScraper
from lametro.events import DuplicateAgendaItemException, LametroEventScraper
from lametro.paired_event_stream import (
    LAMetroAPIEvent,
    LAMetroWebEvent,
    PairedEventStream,
)


@pytest.mark.parametrize(
    "api_status_name,scraper_assigned_status",
    [
        ("Final", "passed"),
        ("Final Revised", "passed"),
        ("Final 2nd Revised", "passed"),
        ("Draft", "confirmed"),
        ("Canceled", "cancelled"),
    ],
)
def test_status_assignment(
    event_scraper,
    api_event,
    web_event,
    api_status_name,
    scraper_assigned_status,
    mocker,
):
    with requests_mock.Mocker() as m:
        matcher = re.compile("webapi.legistar.com")
        m.get(matcher, json={}, status_code=200)

        matcher = re.compile("metro.legistar.com")
        m.get(matcher, json={}, status_code=200)

        api_event["EventAgendaStatusName"] = api_status_name

        mocker.patch(
            "lametro.paired_event_stream.PairedEventStream.merged_events",
            return_value=[(api_event, LAMetroWebEvent(web_event))],
        )

        for event in event_scraper.scrape():
            assert event.status == scraper_assigned_status


@pytest.mark.parametrize(
    "item_sequence,should_error",
    [
        (12, True),
        (11, False),
    ],
)
def test_sequence_duplicate_error(
    event_scraper,
    api_event,
    web_event,
    event_agenda_item,
    item_sequence,
    should_error,
    mocker,
):
    with requests_mock.Mocker() as m:
        matcher = re.compile("webapi.legistar.com")
        m.get(matcher, json={}, status_code=200)

        matcher = re.compile("metro.legistar.com")
        m.get(matcher, json={}, status_code=200)

        api_event["event_details"] = [
            {
                "note": "web",
                "url": "https://metro.legistar.com/MeetingDetail.aspx?ID=642118&GUID=F19B2133-928C-4390-9566-C293C61DC89A&Options=info&Search=",
            }
        ]

        event_agenda_item_b = event_agenda_item.copy()
        event_agenda_item_b["EventItemAgendaSequence"] = item_sequence

        mocker.patch(
            "lametro.paired_event_stream.PairedEventStream.merged_events",
            return_value=[(api_event, LAMetroWebEvent(web_event))],
        )
        mocker.patch(
            "lametro.LametroEventScraper.agenda",
            return_value=[event_agenda_item, event_agenda_item_b],
        )

        if should_error:
            sentry_capture = mocker.patch(
                "lametro.events.capture_exception", autospec=True
            )
            for event in event_scraper.scrape():
                # Should alert Sentry whenever we find an
                # event with duplicate agenda items
                sentry_capture.assert_called_once()
                raised_exc = sentry_capture.call_args[0][0]
                assert isinstance(raised_exc, DuplicateAgendaItemException)

                # Make sure the error message we send is useful
                error_msg = str(raised_exc)
                legistar_api_url = (
                    f"{LametroEventScraper.BASE_URL}/events/{api_event['EventId']}"
                )
                assert legistar_api_url in error_msg
                assert event.name in error_msg
        else:
            for event in event_scraper.scrape():
                assert len(event.agenda) == 2


def test_events_paired(api_event, web_event, mocker):
    mock_scraper = mocker.MagicMock(spec=LAMetroAPIWebEventScraper)
    mock_scraper.event = lambda x: (x, web_event)

    mocker.patch(
        "lametro.paired_event_stream.LAMetroAPIWebEventScraper", return_value=mock_scraper
    )

    # Create a matching SAP event with a distinct ID
    sap_api_event = api_event.copy()
    sap_api_event["EventId"] = 1109
    sap_api_event["EventBodyName"] = "{} (SAP)".format(api_event["EventBodyName"])

    # Set a non-matching time to confirm time is not a match constraint
    sap_api_event["EventTime"] = "12:00 AM"

    # Create a non-matching English event
    another_api_event = api_event.copy()
    another_api_event["EventId"] = 41361
    another_api_event["EventBodyName"] = "Planning and Programming Committee"

    events = [
        api_event,
        sap_api_event,
        another_api_event,
    ]

    results = list(PairedEventStream(events).merged_events)

    # Assert that the scraper yields two events
    assert len(results) == 2

    # Assert that the proper English and Spanish events were paired
    event, _ = results[0]
    assert event["EventId"] == api_event["EventId"]
    assert event["SAPEventId"] == sap_api_event["EventId"]

    # Add a duplicate SAP event to the event array
    # events.append(sap_api_event)

    # Assert duplicates raise an exception
    # with pytest.raises(ValueError) as excinfo:
    #     list(PairedEventStream(events).merged_events)
    # assert (
    #     f"Found duplicate event key '{LAMetroAPIEvent(sap_api_event).own_key}'"
    #     in str(excinfo.value)
    # )


@pytest.mark.parametrize(
    "side_effect,n_results",
    [
        ([None], 0),
        ([("api_event", "web_event"), None], 1),
    ],
    ids=["english_event_discarded", "spanish_event_discarded"],
)
def test_discarded_event_handled(
    request, api_event, mocker, caplog, side_effect, n_results
):
    mock_scraper = mocker.MagicMock(spec=LAMetroAPIWebEventScraper)
    mock_scraper.event = mocker.MagicMock(spec=LAMetroAPIWebEventScraper.event)

    mock_scraper.event.side_effect = [
        tuple(request.getfixturevalue(x) for x in value) if value else None
        for value in side_effect
    ]

    mocker.patch(
        "lametro.paired_event_stream.LAMetroAPIWebEventScraper", return_value=mock_scraper
    )

    # Create a matching SAP event with a distinct ID
    sap_api_event = api_event.copy()
    sap_api_event["EventId"] = 1109
    sap_api_event["EventBodyName"] = "{} (SAP)".format(api_event["EventBodyName"])

    events = [
        api_event,
        sap_api_event,
    ]

    results = list(PairedEventStream(events).merged_events)

    assert len(results) == n_results

    (warning,) = caplog.records

    if request.node.callspec.id == "english_event_discarded":
        assert "English event discarded" in str(warning)
    else:
        assert "Spanish event discarded" in str(warning)
        ((result, _),) = results
        assert len(result["event_details"]) == 1
        assert len(result["audio"]) == 1


@pytest.mark.parametrize("test_case", ["a", "b", "c"])
def test_multiple_minutes_candidates_handling(event_scraper, api_event, test_case):
    """
    The minutes candidates fixture contains a number of test cases:

        1. Attachments that do not have "minutes" on the first page
        2. An attachment that has minutes for another meeting
        3. An attachment that has minutes for the meeting at hand

    This test confirms that we correctly identify the minutes file for
    the meeting at hand and reject the others.
    """

    expected_minutes_title = "Regular Board Meeting MINUTES - September 26, 2024"
    expected_minutes_url = "https://metro.legistar1.com/metro/attachments/73425e96-9569-465d-b4c2-14ef9398e6ee.pdf"

    with requests_mock.Mocker() as m, open(
        Path("tests/fixtures/matter_candidates.json"), "r"
    ) as matter_candidates, open(
        Path("tests/fixtures/minutes_candidates.json"), "r"
    ) as minutes_candidates, open(
        Path("tests/fixtures/wrong_minutes_file.pdf"), "rb"
    ) as wrong_file, open(
        Path(f"tests/fixtures/right_minutes_file_{test_case}.pdf"), "rb"
    ) as right_file:
        m.get(
            re.compile(r"/matters"), json=json.load(matter_candidates), status_code=200
        )
        m.get(
            re.compile(r"/matters/\d+/attachments"),
            json=json.load(minutes_candidates),
            status_code=200,
        )
        m.get(re.compile(r"metro.legistar1.com"), body=BytesIO(), status_code=200)
        m.get(expected_minutes_url, body=right_file, status_code=200)
        m.get(
            "https://metro.legistar1.com/metro/attachments/b9206789-2b9a-4742-9b57-bee1d3d52581.pdf",
            body=wrong_file,
            status_code=200,
        )
        minutes = list(event_scraper.find_approved_minutes(api_event))

    assert len(minutes) == 1
    assert minutes[0]["MatterAttachmentName"] == expected_minutes_title
    assert minutes[0]["MatterAttachmentHyperlink"] == expected_minutes_url
