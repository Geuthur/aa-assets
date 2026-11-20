"""Manager of EveEntity: fetch names from ESI."""

# Standard Library
from typing import TYPE_CHECKING, Any

# Django
from django.db import models

# AA Assets
from assets.app_settings import ASSETS_BULK_BATCH_SIZE
from assets.errors import ObjectNotFound
from assets.providers import esi, logger

if TYPE_CHECKING:
    # AA Assets
    from assets.models import EveEntity as EveEntityContext


class EveEntityManager(models.Manager["EveEntityContext"]):
    def get_or_create_esi(self, *, eve_id: int) -> tuple["EveEntityContext", bool]:
        """gets or creates entity object with data fetched from ESI"""
        # pylint: disable=import-outside-toplevel
        # AA Assets
        from assets.models import EveEntity

        try:
            entity = self.get(id=eve_id)
            return entity, False
        except EveEntity.DoesNotExist:
            return self.update_or_create_esi(eve_id=eve_id)

    def create_bulk_from_esi(self, eve_ids):
        """gets bulk names with ESI"""
        if len(eve_ids) > 0:
            # pylint: disable=import-outside-toplevel
            # AA Assets
            from assets.models import EveEntity

            chunk_size = 500
            id_chunks = [
                eve_ids[i : i + chunk_size] for i in range(0, len(eve_ids), chunk_size)
            ]
            for chunk in id_chunks:
                response = esi.client.Universe.PostUniverseNames(body=chunk).results()
                new_names = []
                logger.debug(
                    "Eve Entity Manager EveName: count in %s count out %s",
                    len(chunk),
                    len(response),
                )
                for entity in response:
                    new_names.append(
                        EveEntity(
                            id=entity.id,
                            name=entity.name,
                            category=entity.category,
                        )
                    )
                EveEntity.objects.bulk_create(
                    new_names,
                    batch_size=ASSETS_BULK_BATCH_SIZE,
                    ignore_conflicts=True,
                )
            return True
        return True

    def update_or_create_esi(self, *, eve_id: int) -> tuple[Any, bool]:
        """updates or creates entity object with data fetched from ESI"""
        response = esi.client.Universe.PostUniverseNames(body=[eve_id]).results()
        if len(response) != 1:
            raise ObjectNotFound(f"Unknown Type with ID {eve_id} not found.")
        entity_data = response[0]
        return self.update_or_create(
            id=entity_data.id,
            defaults={
                "name": entity_data.name,
                "category": entity_data.category,
            },
        )
