# Standard Library
from datetime import datetime
from typing import Any

# Third Party
from ninja import Schema


class Message(Schema):
    message: str


class Character(Schema):
    character_name: str
    character_id: int
    corporation_id: int
    corporation_name: str
    alliance_id: int | None = None
    alliance_name: str | None = None


class Corporation(Schema):
    corporation_id: int
    corporation_name: str
    alliance_id: int | None = None
    alliance_name: str | None = None


class EveName(Schema):
    id: int
    name: str
    cat: str | None = None


class Assets(Schema):
    location_id: int
    location_flag: str
    assets: list


class Requests(Schema):
    id: int
    status: str
    order: Any
    action: str
    created: datetime
    closed: datetime | None = None
    approver: Any | None
    requestor: Any
    actions: Any
