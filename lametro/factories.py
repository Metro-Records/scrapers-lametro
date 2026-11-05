from dataclasses import dataclass
from pupa.scrape import Bill
from pupa.utils import _make_pseudo_id

@dataclass
class OrganizationRef:
    name: str

    @property
    def by_name(self):
        return {"name" : self.name}

    @property
    def by_pseudo_id(self):
        return _make_pseudo_id(**self.by_name)
    
        
def build_bill(*, from_organization: OrganizationRef, **kwargs):
    return Bill(
        from_organization=from_organization.by_name,
        **kwargs
    )

def build_bill_action(*, organization: OrganizationRef, **kwargs):
    return {
        "organization": organization.by_name,
        **kwargs
    }

def add_related_entity(*, action, organization: OrganizationRef):
    action.add_related_entity(
        organization.name,
        "organization",
        entity_id=organization.by_pseudo_id,
    )
    return None


