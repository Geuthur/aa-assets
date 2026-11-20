# Standard Library
from http import HTTPStatus

# Third Party
import pook

# AA Assets
from assets.models import EveEntity
from assets.tests import NoSocketsTestCase
from assets.tests.testdata.esi_urls import clear_esi_limits, universe_names_url


class TestGeneralManager(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = EveEntity.objects

    def setUp(self):
        super().setUp()
        clear_esi_limits()
        self.addCleanup(clear_esi_limits)

    @pook.on
    def test_get_or_create_esi_existing(self):
        """
        Test retrieving an existing EveEntity from the database.

        This test verifies that an existing EveEntity is correctly retrieved
        from the database without making an ESI API call. It checks that the
        entity has the expected eve_id and that the created flag is set to False.

        ### Expected Result
        - EveEntity is retrieved correctly.
        - Entity has correct id.
        - Created flag is False.
        - No ESI request is made.
        """
        # Test Data
        entity = EveEntity.objects.create(
            id=1001, name="Existing Entity", category="character"
        )

        # Test Action
        result, created = self.manager.get_or_create_esi(eve_id=1001)

        # Expected Results
        self.assertEqual(result, entity)
        self.assertFalse(created)
        self.assertEqual(pook.unmatched_requests(), [])

    @pook.on
    def test_get_or_create_esi_new(self):
        """
        Test creating a new EveEntity from ESI data.

        This test verifies that a new EveEntity is correctly created
        based on data fetched from the ESI API. It checks that the entity has the
        expected eve_id and name, and that the created flag is set to True.

        ### Expected Result
        - EveEntity is created correctly.
        - Entity has correct eve_id and name.
        - Created flag is True.
        """
        # Test Data
        mock = pook.post(
            universe_names_url(),
            json=[9996],
            reply=HTTPStatus.OK,
            response_json=[
                {"id": 9996, "name": "Create Character", "category": "character"}
            ],
        )

        # Test Action
        result, created = self.manager.get_or_create_esi(eve_id=9996)

        # Expected Results
        self.assertTrue(mock.isdone())
        self.assertEqual(result.id, 9996)
        self.assertEqual(result.name, "Create Character")
        self.assertTrue(created)

    @pook.on
    def test_create_bulk_from_esi(self):
        """
        Test bulk creation of EveEntity objects from ESI data.

        This test verifies that multiple EveEntity objects are correctly created
        based on data fetched from the ESI API. It checks that the entities with
        the specified eve_ids exist in the database after the operation.

        ### Expected Result
        - Multiple EveEntity objects are created correctly.
        - Entities with specified eve_ids exist in the database.
        """
        # Test Data
        mock = pook.post(
            universe_names_url(),
            json=[9997, 9998],
            reply=HTTPStatus.OK,
            response_json=[
                {"id": 9997, "name": "Bulk Character", "category": "character"},
                {"id": 9998, "name": "Bulk Character 2", "category": "character"},
            ],
        )

        # Test Action
        result = self.manager.create_bulk_from_esi([9997, 9998])

        # Expected Results
        self.assertTrue(mock.isdone())
        self.assertTrue(result)
        self.assertTrue(EveEntity.objects.filter(id=9997).exists())
        self.assertTrue(EveEntity.objects.filter(id=9998).exists())

    @pook.on
    def test_update_or_create_esi(self):
        """
        Test updating or creating an EveEntity from ESI data.

        This test verifies that the EveEntity is correctly updated or created
        based on data fetched from the ESI API. It checks that the entity has the
        expected eve_id and name, and that the created flag is set to True.

        ### Expected Result
        - EveEntity is updated or created correctly.
        - Entity has correct eve_id and name.
        - Created flag is True.
        """
        # Test Data
        mock = pook.post(
            universe_names_url(),
            json=[9999],
            reply=HTTPStatus.OK,
            response_json=[
                {"id": 9999, "name": "New Test Character", "category": "character"}
            ],
        )

        # Test Action
        result, created = self.manager.update_or_create_esi(eve_id=9999)

        # Expected Results
        self.assertTrue(mock.isdone())
        self.assertEqual(result.id, 9999)
        self.assertEqual(result.name, "New Test Character")
        self.assertTrue(created)
