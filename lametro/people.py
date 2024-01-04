from datetime import date
import collections

from legistar.people import LegistarAPIPersonScraper, LegistarPersonScraper

from pupa.scrape import Scraper
from pupa.scrape import Person, Organization


ACTING_MEMBERS_WITH_END_DATE = {"Shirley Choate": date(2018, 10, 24)}

BOARD_OFFICE_ROLES = (
    "Chair",
    "Vice Chair",
    "1st Vice Chair",
    "2nd Vice Chair",
    "Chief Executive Officer",
)

PENDING_COMMITTEE_MEMBERS = ()


class LametroPersonScraper(LegistarAPIPersonScraper, Scraper):
    BASE_URL = "http://webapi.legistar.com/v1/metro"
    WEB_URL = "https://metro.legistar.com"
    TIMEZONE = "America/Los_Angeles"

    def scrape(self):
        """
        Scrape the web to create a dict with all active organizations.
        Then, we can access the correct URL for the organization detail page.
        """
        web_scraper = LegistarPersonScraper(
            requests_per_minute=self.requests_per_minute
        )
        web_scraper.MEMBERLIST = "https://metro.legistar.com/People.aspx"
        web_info = {}
        member_posts = {}

        for member, organizations in web_scraper.councilMembers():
            member_posts[member['Person Name']['label']] = member['Notes']

            for organization, _, _ in organizations:
                organization_name = organization["Department Name"]["label"].strip()
                organization_info = organization["Department Name"]

                web_info[organization_name] = organization_info

        body_types = self.body_types()

        (board_of_directors,) = [
            body
            for body in self.bodies()
            if body["BodyName"] == "Board of Directors - Regular Board Meeting"
        ]
        board_of_directors["BodyName"] = "Board of Directors"

        terms = collections.defaultdict(list)
        for office in self.body_offices(board_of_directors):
            terms[office["OfficeRecordFullName"]].append(office)

        members = {}
        for member, offices in terms.items():
            member = member.replace(" (Interim)", "")
            p = Person(member)

            for term in offices:
                role = term["OfficeRecordTitle"]

                if role not in {"Board Member", "non-voting member"}:
                    p.add_term(
                        role,
                        "legislature",
                        start_date=self.toDate(term["OfficeRecordStartDate"]),
                        end_date=self.toDate(term["OfficeRecordEndDate"]),
                        appointment=True,
                    )

                if role != "Chief Executive Officer":
                    post = member_posts.get(member)

                    if role == "non-voting member":
                        member_type = "Nonvoting Board Member"
                    else:
                        member_type = "Board Member"

                    start_date = self.toDate(term["OfficeRecordStartDate"])
                    end_date = self.toDate(term["OfficeRecordEndDate"])
                    board_membership = p.add_term(
                        member_type,
                        "legislature",
                        district=post,
                        start_date=start_date,
                        end_date=end_date,
                    )

                    acting_member_end_date = ACTING_MEMBERS_WITH_END_DATE.get(p.name)

                    if acting_member_end_date and acting_member_end_date <= end_date:
                        board_membership.extras = {"acting": "true"}

            # Each term contains first and last names. This should be the same
            # across all of a person's terms, so go ahead and grab them from the
            # last term in the array.
            p.family_name = term["OfficeRecordLastName"]
            p.given_name = term["OfficeRecordFirstName"]

            # Defensively assert that the given and family names match the
            # expected value.
            if member == "Hilda L. Solis":
                # Given/family name does not contain middle initial.
                assert p.given_name == "Hilda" and p.family_name == "Solis"
            else:
                assert member == " ".join([p.given_name, p.family_name])

            source_urls = self.person_sources_from_office(term)
            person_api_url, person_web_url = source_urls

            p.add_source(person_api_url, note="api")
            p.add_source(person_web_url, note="web")

            members[member] = p

        for body in self.bodies():
            body_types_list = [
                body_types["Committee"],
                body_types["Independent Taxpayer Oversight Committee"],
            ]

            if (body["BodyTypeId"] in body_types_list) or (
                "test" in body["BodyName"].lower()
            ):
                organization_name = body["BodyName"].strip()

                o = Organization(
                    organization_name,
                    classification="committee",
                    parent_id={"name": "Board of Directors"},
                )

                organization_info = web_info.get(organization_name, {})
                organization_url = organization_info.get(
                    "url", self.WEB_URL + "https://metro.legistar.com/Departments.aspx"
                )

                o.add_source(
                    self.BASE_URL + "/bodies/{BodyId}".format(**body), note="api"
                )
                o.add_source(organization_url, note="web")

                for office in self.body_offices(body):
                    role = office["OfficeRecordTitle"]

                    if role not in BOARD_OFFICE_ROLES:
                        if role == "non-voting member":
                            role = "Nonvoting Member"
                        else:
                            role = "Member"

                    person = office["OfficeRecordFullName"]

                    # Temporarily skip committee memberships, e.g., for
                    # new board members. The content of this array is provided
                    # by Metro.
                    if person in PENDING_COMMITTEE_MEMBERS:
                        self.warning(
                            "Skipping {0} membership for {1}".format(
                                organization_name, person
                            )
                        )
                        continue

                    if person in members:
                        p = members[person]
                    else:
                        p = Person(person)

                        source_urls = self.person_sources_from_office(office)
                        person_api_url, person_web_url = source_urls
                        p.add_source(person_api_url, note="api")
                        p.add_source(person_web_url, note="web")

                        members[person] = p

                    start_date = self.toDate(office["OfficeRecordStartDate"])
                    end_date = self.toDate(office["OfficeRecordEndDate"])
                    membership = p.add_membership(
                        organization_name,
                        role=role,
                        start_date=start_date,
                        end_date=end_date,
                    )

                    acting_member_end_date = ACTING_MEMBERS_WITH_END_DATE.get(p.name)
                    if acting_member_end_date and acting_member_end_date <= end_date:
                        membership.extras = {"acting": "true"}

                yield o

        for p in members.values():
            yield p
