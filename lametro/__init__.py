# encoding=utf-8
from pupa.scrape import Jurisdiction, Organization
from .bills import LametroBillScraper
from .people import LametroPersonScraper
from .events import LametroEventScraper
from datetime import datetime


class Lametro(Jurisdiction):
    division_id = "ocd-division/country:us/state:ca/county:los_angeles"
    classification = "transit_authority"
    name = "Los Angeles County Metropolitan Transportation Authority"
    url = "https://www.metro.net/"
    scrapers = {
        "bills": LametroBillScraper,
        "people": LametroPersonScraper,
        "events": LametroEventScraper,
    }

    @property
    def legislative_sessions():
        '''
        Yield each year that we'd like to scrape today.
        Allow for the next fiscal year to be scraped during
        and after the last week of the current fiscal year.
        '''
        today = datetime.now()
        this_year = today.year
        allowed_years = list(range(2014, this_year))

        if (today.month == 6 and today.day >= 23) or today.month >= 7:
            # The last week of this fiscal year has begun. Start scraping the next year
            allowed_years.append(this_year)

        for year in allowed_years:
            session = {
                "identifier": "{}".format(year),
                "start_date": "{}-07-01".format(year),
                "end_date": "{}-06-30".format(year + 1),
            }
            yield session


    def get_organizations(self):
        org = Organization(name="Board of Directors", classification="legislature")

        org.add_post(
            "Mayor of the City of Los Angeles",
            "Board Member",
            division_id="ocd-division/country:us/state:ca/place:los_angeles",
        )

        for district in range(1, 6):
            org.add_post(
                "Los Angeles County Board Supervisor, District {}".format(district),
                "Board Member",
                division_id="ocd-division/country:us/state:ca/county:los_angeles/council_district:{}".format(
                    district
                ),
            )

        org.add_post(
            "Appointee of the Mayor of the City of Los Angeles",
            "Board Member",
            division_id="ocd-division/country:us/state:ca/place:los_angeles",
        )

        org.add_post(
            "Appointee of Governor of California",
            "Nonvoting Board Member",
            division_id="ocd-division/country:us/state:ca",
        )

        org.add_post(
            "District 7 Director, California Department of Transportation (Caltrans), Appointee of the Governor of California",
            "Nonvoting Board Member",
            division_id="ocd-division/country:us/state:ca/transit:caltrans/district:7",
        )

        org.add_post(
            "District 7 Director (Interim), California Department of Transportation (Caltrans), Appointee of the Governor of California",
            "Nonvoting Board Member",
            division_id="ocd-division/country:us/state:ca/transit:caltrans/district:7",
        )

        org.add_post(
            "Appointee of the Los Angeles County City Selection Committee, North County/San Fernando Valley sector",
            "Board Member",
            division_id="ocd-division/country:us/state:ca/county:los_angeles/la_metro_sector:north_county_san_fernando_valley",
        )

        org.add_post(
            "Appointee of Los Angeles County City Selection Committee, Southwest Corridor sector",
            "Board Member",
            division_id="ocd-division/country:us/state:ca/county:los_angeles/la_metro_sector:southwest_corridor",
        )

        org.add_post(
            "Appointee of Los Angeles County City Selection Committee, San Gabriel Valley sector",
            "Board Member",
            division_id="ocd-division/country:us/state:ca/county:los_angeles/la_metro_sector:san_gabriel_valley",
        )

        org.add_post(
            "Appointee of Los Angeles County City Selection Committee, South East Long Beach sector",
            "Board Member",
            division_id="ocd-division/country:us/state:ca/county:los_angeles/la_metro_sector:southeast_long_beach",
        )

        org.add_post("Chair", "Chair")

        org.add_post("Vice Chair", "Vice Chair")

        org.add_post("1st Vice Chair", "1st Vice Chair")

        org.add_post("2nd Vice Chair", "2nd Vice Chair")

        org.add_post("Chief Executive Officer", "Chief Executive Officer")

        org.add_source(
            "https://metro.legistar.com/DepartmentDetail.aspx?ID=28529&GUID=44319A1A-B2B7-48CC-B857-ADCE9064573B",
            note="web",
        )

        yield org

        org = Organization(
            name="Crenshaw Project Corporation", classification="corporation"
        )
        org.add_source(
            "https://metro.legistar.com/DepartmentDetail.aspx?ID=32216&GUID=D790CC05-ACCB-451C-B576-2952090769F1"
        )
        yield org

        org = Organization(name="LA SAFE", classification="corporation")
        org.add_source(
            "https://metro.legistar.com/DepartmentDetail.aspx?ID=30222&GUID=5F27DA83-633F-4FEA-A4B0-0477551061B6&R=aef57793-1826-4cfa-b6e3-d6b42cf77527"
        )
        yield org

        org = Organization(name="Special Board Budget Workshop", classification="committee")

        org.add_source("https://metro.legistar.com/DepartmentDetail.aspx?ID=52282&GUID=2FFCEDD3-18CA-4895-9998-8F9A2F533E4F&R=5c9ccace-e519-461a-9c62-aa987ea49f67")
        
        yield org
