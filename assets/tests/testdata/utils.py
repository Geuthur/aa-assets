# Third Party
from evesde_factory.utils import add_character_to_user

# Django
from django.contrib.auth.models import User

# Alliance Auth
from allianceauth.authentication.backends import StateBackend
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter
from allianceauth.tests.auth_utils import AuthUtils

# AA Assets
from assets.models import Owner


def create_user_from_evecharacter(
    character_id: int,
    permissions: list[str] | None = None,
    scopes: list[str] | None = None,
) -> tuple[User, CharacterOwnership]:
    """Create new allianceauth user from EveCharacter object.

    Args:
        character_id (int): ID of eve character
        permissions (list[str] | None): list of permission names, e.g. `"my_app.my_permission"`
        scopes (list[str] | None): list of scope names
    Returns:
        tuple(User, CharacterOwnership): Created Alliance Auth User and CharacterOwnership
    """
    auth_character = EveCharacter.objects.get(character_id=character_id)
    user = AuthUtils.create_user(auth_character.character_name.replace(" ", "_"))
    character_ownership = add_character_to_user(
        user, auth_character, is_main=True, scopes=scopes
    )
    if permissions:
        for permission_name in permissions:
            user = AuthUtils.add_permission_to_user_by_name(permission_name, user)
    return user, character_ownership


def create_assets_owner(character: EveCharacter, **kwargs) -> Owner:
    """
    Create a Owner (Owner) from an EveCharacter.
    Args:
        character (EveCharacter): The EveCharacter to create the owner from.
    Returns:
        Owner: The created assets owner.

    """
    defaults = {
        "is_active": True,
    }
    defaults.update(kwargs)
    owner = Owner.objects.get_or_create(
        character=character,
        defaults=defaults,
    )[0]
    return owner


def create_owner_from_user(user: User, **kwargs) -> Owner:
    """
    Create a assets owner from a user.

    Args:
        user (User): The user to create the owner from.
    """
    character = user.profile.main_character.character_ownership
    if not character:
        raise ValueError("User needs to have a main character.")

    return create_assets_owner(character, **kwargs)


def create_owner_from_evecharacter(character_id: int, **kwargs) -> Owner:
    """
    Create a assets owner from an existing EveCharacter.

    Args:
        character_id (int): ID of the EveCharacter to create the owner from.
    Returns:
        Owner: The created assets owner.
    """

    _, character_ownership = create_user_from_evecharacter_with_access(
        character_id, disconnect_signals=True
    )
    return create_assets_owner(character_ownership.character, **kwargs)


def create_user_from_evecharacter_with_access(
    character_id: int, disconnect_signals: bool = True
) -> tuple[User, CharacterOwnership]:
    """
    Create user with basic access from an existing EveCharacter and use it as main.

    Args:
        character_id (int): ID of eve character
        disconnect_signals (bool, optional): Whether to disconnect signals during user creation. Defaults to True.
    Returns:
        tuple(User, CharacterOwnership): Created Alliance Auth User and CharacterOwnership
    """
    auth_character = EveCharacter.objects.get(character_id=character_id)
    username = StateBackend.iterate_username(auth_character.character_name)
    user = AuthUtils.create_user(username, disconnect_signals=disconnect_signals)
    user = AuthUtils.add_permission_to_user_by_name(
        "assets.basic_access", user, disconnect_signals=disconnect_signals
    )

    scopes = Owner.get_esi_scopes()

    character_ownership = add_character_to_user(
        user,
        auth_character,
        is_main=True,
        scopes=scopes,
        disconnect_signals=disconnect_signals,
    )
    return user, character_ownership


def add_new_permission_to_user(
    user: User,
    permission_name: str,
    disconnect_signals: bool = True,
) -> User:
    """Add a new permission to an existing allianceauth user.

    Args:
        user (User): Alliance Auth User
        permission_name (str): Permission name, e.g. `"my_app.my_permission"`
        disconnect_signals (bool, optional): Whether to disconnect signals during addition. Defaults to True.
    Returns:
        User: Updated Alliance Auth User
    """
    return AuthUtils.add_permission_to_user_by_name(
        permission_name, user, disconnect_signals=disconnect_signals
    )


def add_auth_character_to_user(
    user: User,
    character_id: int,
    disconnect_signals: bool = True,
    owner_type="character",
) -> CharacterOwnership:
    """Add an existing :class:`EveCharacter` to a User.

    Args:
        user (User): Alliance Auth User
        character_id (int): ID of eve character
        disconnect_signals (bool, optional): Whether to disconnect signals during addition. Defaults to True.
        owner_type (str, optional): Type of owner, either "character" or "corporation"
    Returns:
        CharacterOwnership: The created CharacterOwnership instance.
    """
    auth_character = EveCharacter.objects.get(character_id=character_id)

    scopes = Owner.get_esi_scopes()

    return add_character_to_user(
        user,
        auth_character,
        is_main=False,
        scopes=scopes,
        disconnect_signals=disconnect_signals,
    )


def add_owner_to_user(
    user: User,
    character_id: int,
    disconnect_signals: bool = True,
    owner_type="character",
    **kwargs,
) -> Owner:
    """
    Add a CharacterOwner or CorporationOwner character to a user.
    The type of owner created depends on the owner_type parameter.

    Args:
        user (User): Alliance Auth User
        character_id (int): ID of eve character
        disconnect_signals (bool, optional): Whether to disconnect signals during addition. Defaults to True.
        owner_type (str): Type of owner, either "character" or "corporation"
    Returns:
        CharacterOwner | CorporationOwner: The created owner.
    """
    character_ownership = add_auth_character_to_user(
        user,
        character_id,
        disconnect_signals=disconnect_signals,
    )
    return create_assets_owner(
        character_ownership.character, owner_type=owner_type, **kwargs
    )
