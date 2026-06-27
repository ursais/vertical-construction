from odoo import fields, models
from odoo.exceptions import UserError


class ConstructionBudgetImportCatalogTemplate(models.TransientModel):
    _name = "construction.budget.import.catalog.template"
    _description = "Import Catalog APU Templates into Budget"

    version_id = fields.Many2one(
        "construction.budget.version",
        string="Budget Version",
        required=True,
        readonly=True,
    )
    chapter_id = fields.Many2one(
        "construction.budget.chapter",
        string="Chapter",
        required=True,
        domain="[('version_id', '=', version_id)]",
    )
    catalog_version_id = fields.Many2one(
        related="version_id.budget_id.catalog_version_id",
        readonly=True,
    )
    template_ids = fields.Many2many(
        "construction.catalog.template",
        string="Templates",
        domain="[('catalog_version_id', '=', catalog_version_id)]",
    )

    def action_import(self):
        self.ensure_one()
        if not self.template_ids:
            raise UserError(self.env._("Select at least one APU template to import."))
        if self.version_id.is_frozen:
            raise UserError(
                self.env._(
                    "Cannot import templates into frozen version '%(name)s'.",
                    name=self.version_id.display_name,
                )
            )
        for template in self.template_ids:
            template.create_budget_line(self.version_id, self.chapter_id)
        return {"type": "ir.actions.act_window_close"}
