from datetime import datetime

import pytest
from freezegun import freeze_time
from lametro import Lametro


@pytest.mark.parametrize("test_date", [
    '2024-06-10',  # before the last week of the fiscal year
    '2024-06-23',  # start of the last week of the fiscal year
    '2024-10-01',  # well after the last week
    '2024-12-24',  # last week of regular year
    '2025-05-01',  # before the last week of the next fiscal year
    '2025-06-30'   # end of the last week of the next fiscal year
])
def test_legislative_sessions(test_date):
    '''
    Test that next fiscal year's legislative sessions are included
    only when it's the last week of the current one.
    '''
    date_format = "%Y-%m-%d"
    test_year = test_date.split('-')[0]
    last_week_of_year = datetime.strptime(f"{test_year}-06-23", date_format).date()

    with freeze_time(test_date):
        fake_now = datetime.now()
        fake_date = fake_now.date()
        next_year = str(fake_now.year + 1)  

        sessions = list(Lametro.legislative_sessions.fget())
        latest_session_date = sessions[-1]["end_date"]

        if fake_date < last_week_of_year:
            assert next_year not in latest_session_date
        elif fake_date >= last_week_of_year:
            assert next_year in latest_session_date
