from dataclasses import dataclass
from pupa.scrape import Bill

@dataclass
class OrganizationName:
    name: str

def build_bill(*, from_organization: OrganizationName, **kwargs):
    return Bill(from_organization=from_organization, **kwargs)

def build_bill_action(*, organization: OrganizationName, **kwargs):
    return {"organization": organization, **kwargs}
