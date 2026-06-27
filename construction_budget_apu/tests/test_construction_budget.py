from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestConstructionBudgetApu(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Projects"}
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Test Construction Analytic",
                "plan_id": cls.analytic_plan.id,
            }
        )
        cls.expense_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", cls.env.company.id),
            ],
            limit=1,
        )
        cls.budget_post = cls.env["account.budget.post"].create(
            {
                "name": "Construction Costs",
                "account_ids": [(6, 0, cls.expense_account.ids)],
            }
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Construction Project",
                "account_id": cls.analytic_account.id,
            }
        )
        cls.budget = cls.env["construction.budget"].create(
            {
                "project_id": cls.project.id,
                "analytic_account_id": cls.analytic_account.id,
                "default_budget_post_id": cls.budget_post.id,
            }
        )
        cls.version = cls.env["construction.budget.version"].create(
            {
                "budget_id": cls.budget.id,
                "version_number": 1,
                "name": "V1",
            }
        )
        cls.budget.current_version_id = cls.version
        cls.chapter = cls.env["construction.budget.chapter"].create(
            {
                "version_id": cls.version.id,
                "code": "01",
                "name": "General",
            }
        )

    def test_apu_computes_unit_price(self):
        line = self.env["construction.budget.line"].create(
            {
                "version_id": self.version.id,
                "chapter_id": self.chapter.id,
                "name": "Test line",
                "quantity": 2,
            }
        )
        self.env["construction.budget.apu.component"].create(
            {
                "apu_id": line.apu_id.id,
                "name": "Material",
                "component_type": "material",
                "quantity": 1,
                "unit_cost": 10,
                "waste_percent": 10,
            }
        )
        self.assertAlmostEqual(line.apu_id.unit_price, 11.0)
        self.assertAlmostEqual(line.unit_price, 11.0)
        self.assertAlmostEqual(line.subtotal, 22.0)

    def test_version_approval_and_freeze(self):
        line = self.env["construction.budget.line"].create(
            {
                "version_id": self.version.id,
                "chapter_id": self.chapter.id,
                "name": "Frozen line",
                "quantity": 1,
                "apu_mode": False,
                "unit_price": 100,
            }
        )
        self.version.action_submit()
        self.assertEqual(self.version.state, "submitted")
        self.version.action_approve()
        self.assertEqual(self.version.state, "approved")
        self.assertTrue(self.version.crossovered_budget_id)
        self.assertEqual(self.version.crossovered_budget_id.state, "confirm")
        self.version.action_freeze()
        self.assertTrue(self.version.is_frozen)
        self.assertEqual(self.version.crossovered_budget_id.state, "validate")
        with self.assertRaises(UserError):
            line.write({"name": "Should fail"})

    def test_sync_crossovered_budget_aggregates_by_budget_post(self):
        chapter_material = self.env["construction.budget.chapter"].create(
            {
                "version_id": self.version.id,
                "code": "02",
                "name": "Materials",
                "budget_post_id": self.budget_post.id,
            }
        )
        other_post = self.env["account.budget.post"].create(
            {
                "name": "Labor Costs",
                "account_ids": [(6, 0, self.expense_account.ids)],
            }
        )
        chapter_labor = self.env["construction.budget.chapter"].create(
            {
                "version_id": self.version.id,
                "code": "03",
                "name": "Labor",
                "budget_post_id": other_post.id,
            }
        )
        self.env["construction.budget.line"].create(
            {
                "version_id": self.version.id,
                "chapter_id": chapter_material.id,
                "name": "Material line",
                "quantity": 1,
                "apu_mode": False,
                "unit_price": 100,
            }
        )
        self.env["construction.budget.line"].create(
            {
                "version_id": self.version.id,
                "chapter_id": chapter_labor.id,
                "name": "Labor line",
                "quantity": 1,
                "apu_mode": False,
                "unit_price": 50,
            }
        )
        self.version.action_submit()
        self.version.action_approve()
        crossovered = self.version.crossovered_budget_id
        self.assertEqual(len(crossovered.crossovered_budget_line_ids), 2)
        planned = {
            line.general_budget_id.id: line.planned_amount
            for line in crossovered.crossovered_budget_line_ids
        }
        self.assertAlmostEqual(planned[self.budget_post.id], -100.0)
        self.assertAlmostEqual(planned[other_post.id], -50.0)

    def test_sync_requires_default_budget_post(self):
        budget = self.env["construction.budget"].create(
            {
                "project_id": self.project.id,
                "analytic_account_id": self.analytic_account.id,
            }
        )
        version = self.env["construction.budget.version"].create(
            {
                "budget_id": budget.id,
                "version_number": 1,
                "name": "No post",
            }
        )
        chapter = self.env["construction.budget.chapter"].create(
            {
                "version_id": version.id,
                "name": "General",
            }
        )
        self.env["construction.budget.line"].create(
            {
                "version_id": version.id,
                "chapter_id": chapter.id,
                "name": "Line",
                "quantity": 1,
                "apu_mode": False,
                "unit_price": 10,
            }
        )
        version.action_submit()
        with self.assertRaises(UserError):
            version.action_approve()

    def test_version_copy_and_compare(self):
        self.env["construction.budget.line"].create(
            {
                "version_id": self.version.id,
                "chapter_id": self.chapter.id,
                "code": "01.01",
                "name": "Base item",
                "quantity": 1,
                "apu_mode": False,
                "unit_price": 50,
            }
        )
        version_2 = self.env["construction.budget.version"].create(
            {
                "budget_id": self.budget.id,
                "version_number": 2,
                "name": "V2",
            }
        )
        self.version.copy_structure_to(version_2)
        self.assertEqual(len(version_2.line_ids), 1)
        version_2.line_ids.unit_price = 75
        compare = self.env["construction.budget.version.compare"].create(
            {
                "budget_id": self.budget.id,
                "version_a_id": self.version.id,
                "version_b_id": version_2.id,
            }
        )
        compare.action_generate()
        modified = compare.line_ids.filtered(
            lambda compare_line: compare_line.change_type == "modified"
        )
        self.assertEqual(len(modified), 1)
        self.assertAlmostEqual(modified.subtotal_delta, 25.0)

    def test_create_new_version_from_budget(self):
        self.env["construction.budget.line"].create(
            {
                "version_id": self.version.id,
                "chapter_id": self.chapter.id,
                "name": "Seed line",
                "quantity": 1,
                "apu_mode": False,
                "unit_price": 10,
            }
        )
        action = self.budget.action_create_version()
        new_version = self.env["construction.budget.version"].browse(action["res_id"])
        self.assertEqual(new_version.version_number, 2)
        self.assertEqual(len(new_version.line_ids), 1)

    def test_import_catalog_template_and_snapshot(self):
        catalog_version = self.env["construction.catalog.version"].create(
            {
                "name": "Budget Catalog",
                "code": "BCAT-2025",
                "date_start": "2025-01-01",
                "state": "active",
            }
        )
        concept = self.env["construction.catalog.concept"].create(
            {
                "catalog_version_id": catalog_version.id,
                "code": "C100",
                "name": "Imported concept",
            }
        )
        catalog_input = self.env["construction.catalog.input"].create(
            {
                "catalog_version_id": catalog_version.id,
                "code": "I100",
                "name": "Imported input",
                "input_type": "material",
                "unit_cost": 5.0,
            }
        )
        template = self.env["construction.catalog.template"].create(
            {
                "catalog_version_id": catalog_version.id,
                "code": "T100",
                "name": "Imported template",
                "concept_id": concept.id,
            }
        )
        self.env["construction.catalog.template.line"].create(
            {
                "template_id": template.id,
                "input_id": catalog_input.id,
                "quantity": 2.0,
                "unit_cost": 5.0,
            }
        )
        self.budget.catalog_version_id = catalog_version
        wizard = self.env["construction.budget.import.catalog.template"].create(
            {
                "version_id": self.version.id,
                "chapter_id": self.chapter.id,
                "template_ids": [(6, 0, template.ids)],
            }
        )
        wizard.action_import()
        self.assertEqual(len(self.version.line_ids), 1)
        line = self.version.line_ids
        self.assertEqual(line.catalog_template_id, template)
        self.assertAlmostEqual(line.unit_price, 10.0)
        self.version.action_submit()
        self.version.action_approve()
        self.version.action_freeze()
        self.assertTrue(self.budget.catalog_snapshot_id)
        self.assertEqual(
            self.budget.catalog_snapshot_id.catalog_version_id,
            catalog_version,
        )
