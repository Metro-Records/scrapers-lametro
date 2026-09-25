from dataclasses import dataclass
from pupa.scrape import Bill
from pupa.utils import _make_pseudo_id

@dataclass
class OrganizationRef:
    name: str

    @property
    def as_dict(self):
        return {"name" : self.name}

    @property
    def by_pseudo_id(self):
        return _make_pseudo_id(name=self.name)
    
def checkOrgRef(arg):
    if isinstance(arg, OrganizationRef):
        return True
    else:
        raise TypeError(f"Keyword ${arg} expected argument of type OrganizationRef")

def build_bill(*, from_organization: OrganizationRef, **kwargs):
    if checkOrgRef(from_organization):
        return Bill(
            from_organization=from_organization.as_dict,
            **kwargs
        )

def build_bill_action(*, organization: OrganizationRef, **kwargs):
    if checkOrgRef(organization):
        return {
            "organization": organization.as_dict,
            **kwargs
        }

def add_related_entity_org(*, action, organization: OrganizationRef):
    if checkOrgRef(organization):
        action.add_related_entity(
            organization.name,
            "organization",
            entity_id=organization.by_pseudo_id,
        )
