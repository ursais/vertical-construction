from odoo import models
from odoo.exceptions import UserError


class ConstructionCatalogTemplateBudget(models.Model):
    _inherit = "construction.catalog.template"

    def create_budget_line(self, version, chapter):
        """Create a budget line with APU components copied from this template."""
        self.ensure_one()
        version.ensure_one()
        chapter.ensure_one()
        if version.is_frozen:
            raise UserError(
                self.env._(
                    "Cannot import templates into frozen version '%(name)s'.",
                    name=version.display_name,
                )
            )
        apu = self.env["construction.budget.apu"].create(
            {
                "name": self.name,
                "reference": self.code,
            }
        )
        component_model = self.env["construction.budget.apu.component"]
        for line in self.line_ids.sorted("sequence"):
            component_model.create(
                {
                    "apu_id": apu.id,
                    "name": line.input_id.name,
                    "component_type": line.input_type,
                    "product_id": line.input_id.product_id.id,
                    "quantity": line.quantity,
                    "uom_id": line.uom_id.id,
                    "unit_cost": line.unit_cost,
                    "waste_percent": line.waste_percent,
                    "notes": line.notes,
                }
            )
        return self.env["construction.budget.line"].create(
            {
                "version_id": version.id,
                "chapter_id": chapter.id,
                "code": self.concept_id.code,
                "name": self.concept_id.name,
                "uom_id": self.uom_id.id,
                "apu_id": apu.id,
                "catalog_template_id": self.id,
            }
        )
