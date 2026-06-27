from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestConstructionMasterCatalog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.version = cls.env["construction.catalog.version"].create(
            {
                "name": "Test Catalog",
                "code": "TEST-2025",
                "date_start": "2025-01-01",
                "state": "draft",
            }
        )
        cls.concept = cls.env["construction.catalog.concept"].create(
            {
                "catalog_version_id": cls.version.id,
                "code": "C01",
                "name": "Test concept",
            }
        )
        cls.catalog_input = cls.env["construction.catalog.input"].create(
            {
                "catalog_version_id": cls.version.id,
                "code": "I01",
                "name": "Test input",
                "input_type": "material",
                "unit_cost": 10.0,
            }
        )

    def test_template_computes_unit_price(self):
        template = self.env["construction.catalog.template"].create(
            {
                "catalog_version_id": self.version.id,
                "code": "T01",
                "name": "Test template",
                "concept_id": self.concept.id,
            }
        )
        self.env["construction.catalog.template.line"].create(
            {
                "template_id": template.id,
                "input_id": self.catalog_input.id,
                "quantity": 2.0,
                "unit_cost": 10.0,
                "waste_percent": 10.0,
            }
        )
        self.assertAlmostEqual(template.unit_price, 22.0)

    def test_closed_version_blocks_edits(self):
        self.version.action_activate()
        self.version.action_close()
        with self.assertRaises(UserError):
            self.concept.write({"name": "Changed"})

    def test_copy_catalog_to_new_version(self):
        self.version.action_activate()
        crew = self.env["construction.catalog.crew"].create(
            {
                "catalog_version_id": self.version.id,
                "code": "CR01",
                "name": "Test crew",
            }
        )
        self.env["construction.catalog.crew.line"].create(
            {
                "crew_id": crew.id,
                "input_id": self.catalog_input.id,
                "quantity": 2.0,
                "unit_cost": 10.0,
            }
        )
        new_version = self.version.copy_catalog_to(
            {
                "name": "Test Catalog 2026",
                "code": "TEST-2026",
                "date_start": "2026-01-01",
            }
        )
        self.assertEqual(new_version.state, "draft")
        self.assertEqual(len(new_version.concept_ids), 1)
        self.assertEqual(len(new_version.input_ids), 1)
        self.assertEqual(len(new_version.crew_ids), 1)
        self.assertEqual(len(new_version.crew_ids.line_ids), 1)

    def test_create_snapshot_from_closed_version(self):
        self.version.action_activate()
        self.version.action_close()
        snapshot = self.env["construction.catalog.snapshot"].create(
            {
                "name": self.version.name,
                "catalog_version_id": self.version.id,
                "reference": "PROJECT-001",
            }
        )
        self.assertEqual(snapshot.catalog_version_id, self.version)
        self.assertEqual(snapshot.date_start, self.version.date_start)
