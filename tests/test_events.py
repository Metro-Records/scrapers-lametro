import pytest
import requests_mock
import requests
import re

from pupa.scrape.event import Event

from lametro.events import LAMetroAPIEvent, LAMetroWebEvent


@pytest.mark.parametrize('api_status_name,scraper_assigned_status', [
    ('Final', 'passed'),
    ('Final Revised', 'passed'),
    ('Final 2nd Revised', 'passed'),
    ('Draft', 'confirmed'),
    ('Canceled', 'cancelled')
])
def test_status_assignment(event_scraper,
                           api_event,
                           web_event,
                           api_status_name,
                           scraper_assigned_status,
                           mocker):
    with requests_mock.Mocker() as m:
        matcher = re.compile('webapi.legistar.com')
        m.get(matcher, json={}, status_code=200)

        matcher = re.compile('metro.legistar.com')
        m.get(matcher, json={}, status_code=200)

        api_event['EventAgendaStatusName'] = api_status_name

        mocker.patch('lametro.LametroEventScraper._merge_events', return_value=[(api_event, LAMetroWebEvent(web_event))])

        for event in event_scraper.scrape():
            assert event.status == scraper_assigned_status


def test_events_paired(event_scraper, api_event, web_event, mocker):
    # Create a matching SAP event with a distinct ID
    sap_api_event = api_event.copy()
    sap_api_event['EventId'] = 1109
    sap_api_event['EventBodyName'] = '{} (SAP)'.format(api_event['EventBodyName'])

    # Set a non-matching time to confirm time is not a match constraint
    sap_api_event['EventTime'] = '12:00 AM'

    # Create a non-matching English event
    another_api_event = api_event.copy()
    another_api_event['EventId'] = 41361
    another_api_event['EventBodyName'] = 'Planning and Programming Committee'

    events = [
        (LAMetroAPIEvent(api_event), web_event),
        (LAMetroAPIEvent(sap_api_event), web_event),
        (LAMetroAPIEvent(another_api_event), web_event)
    ]

    results = event_scraper._merge_events(events)

    # Assert that the scraper yields two events
    assert len(results) == 2

    # Assert that the proper English and Spanish events were paired
    event, web_event = results[0]
    assert event['EventId'] == api_event['EventId']
    assert event['SAPEventId'] == sap_api_event['EventId']

    # Add a duplicate SAP event to the event array
    events.append((LAMetroAPIEvent(sap_api_event), web_event))

    # Assert that duplicate SAP events raise an exception
    with pytest.raises(ValueError) as excinfo:
        event_scraper._merge_events(events)

        event_key = LAMetroAPIEvent(sap_api_event).key
        assert '{} already exists as a key'.format(event_key) in str(excinfo.value)
