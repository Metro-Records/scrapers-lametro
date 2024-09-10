from datetime import datetime

import pytest
from freezegun import freeze_time


@freeze_time('2024-06-23')
def test_legislative_session(mocker):
    '''
    Test that next fiscal year's legislative sessions are included
    when it's the last week of the current one.
    '''
    fake_now = datetime.now()
    mocker.patch(
        "lametro.Lametro.today", return_value=fake_now
    )
    from lametro import Lametro

    latest_session_date = Lametro.legislative_sessions[-1]["end_date"]
    next_year = str(fake_now.year + 1)

    assert next_year in latest_session_date
    breakpoint()
