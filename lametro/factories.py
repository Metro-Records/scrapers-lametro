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
    def as_pseudo_id(self):
        return _make_pseudo_id(name=self.name)
    

def build_bill(*, from_organization: OrganizationRef, **kwargs) -> Bill:
    if isinstance(from_organization, OrganizationRef):
        return Bill(
            from_organization=from_organization.as_dict,
            **kwargs
        )
    else:
        raise TypeError(f"Parameter from_organization expected argument of type OrganizationRef")


def build_bill_action(*, organization: OrganizationRef, **kwargs) -> dict:
    if isinstance(organization, OrganizationRef):
        return {
            "organization": organization.as_dict,
            **kwargs
        }
    else:
        raise TypeError(f"Parameter from_organization expected argument of type OrganizationRef")


def add_related_entity_org(*, action, organization: OrganizationRef) -> None:
    if isinstance(from_organization, OrganizationRef):
        action.add_related_entity(
            organization.name,
            "organization",
            entity_id=organization.as_pseudo_id,
        )
    else:
        raise TypeError(f"Parameter from_organization expected argument of type OrganizationRef")

