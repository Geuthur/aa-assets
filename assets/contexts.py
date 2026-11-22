class GetUniverseStructuresStructureIdContext:
    class Position:
        x: int
        y: int
        z: int

    name: str
    owner_id: int
    position: Position
    solar_system_id: int
    type_id: int


class GetAssetsContext:
    is_blueprint_copy: bool
    is_singleton: bool
    item_id: int
    location_flag: str
    location_id: int
    location_type: str
    quantity: int
    type_id: int
