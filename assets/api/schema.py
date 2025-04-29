from datetime import datetime
from typing import Any, Optional

from ninja import Schema


class Message(Schema):
    message: str


class Character(Schema):
    character_name: str
    character_id: int
    corporation_id: int
    corporation_name: str
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None


class Corporation(Schema):
    corporation_id: int
    corporation_name: str
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None


class EveName(Schema):
    id: int
    name: str
    cat: Optional[str] = None


class Assets(Schema):
    item_id: int
    name: str
    quantity: int
    location_id: int
    location: str
    price: Any


class Requests(Schema):
    id: int
    status: str
    order: Any
    action: str
    created: datetime
    closed: Optional[datetime] = None
    approver: Optional[Any]
    requestor: Any
    actions: Any
