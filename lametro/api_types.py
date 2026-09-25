from typing import TypedDict

class Matter(TypedDict):
    MatterFile: str
    MatterId: int
    MatterIntroDate: str
    MatterTitle: str
    MatterBodyName: str
    MatterTypeName: str
    MatterRestrictViewViaWeb: bool
    MatterStatusName: str
    MatterVersion: int
    legistar_url: str
