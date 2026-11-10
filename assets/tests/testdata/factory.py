# Third Party
import factory
from evesde_factory.allianceauth import EveCharacterFactory, UserFactory
from evesde_factory.utils import add_character_to_user

# AA Assets
from assets import __app_name__


class UserMainFactory(UserFactory):
    """Generate a User object with a main character and default permissions for Assets."""

    permissions__ = [f"{__app_name__}.basic_access"]
    scopes__ = [
        "esi-universe.read_structures.v1",
        "esi-assets.read_assets.v1",
        "esi-assets.read_corporation_assets.v1",
    ]

    # pylint: disable=no-self-argument
    @factory.post_generation
    def main_character(obj, create, _, **kwargs):
        if not create:
            return
        if "character" in kwargs:
            character = kwargs["character"]
        else:
            character_name = f"{obj.first_name} {obj.last_name}"
            character = EveCharacterFactory(character_name=character_name)

        add_character_to_user(
            user=obj,
            character=character,
            is_main=True,
            scopes=obj._main_character_scopes,
        )
