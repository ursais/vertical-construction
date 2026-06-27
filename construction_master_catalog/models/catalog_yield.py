from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ConstructionCatalogYield(models.Model):
    _name = "construction.catalog.yield"
    _description = "Construction Yield (Rendimiento)"
    _inherit = "construction.catalog.mixin.version"
    _order = "concept_id, id"

    concept_id = fields.Many2one(
        "construction.catalog.concept",
        string="Concept",
        required=True,
        ondelete="cascade",
        domain="[('catalog_version_id', '=', catalog_version_id)]",
        index=True,
    )
    input_id = fields.Many2one(
        "construction.catalog.input",
        string="Input",
        domain="[('catalog_version_id', '=', catalog_version_id)]",
        index=True,
    )
    crew_id = fields.Many2one(
        "construction.catalog.crew",
        string="Crew",
        domain="[('catalog_version_id', '=', catalog_version_id)]",
        index=True,
    )
    yield_quantity = fields.Float(
        string="Yield Quantity",
        required=True,
        digits="Product Unit of Measure",
        help="Output quantity per unit of resource (concept UoM per input/crew unit).",
    )
    resource_quantity = fields.Float(
        string="Resource Quantity",
        default=1.0,
        digits="Product Unit of Measure",
        help="Base quantity of input or crew days used for the yield.",
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Yield UoM",
        related="concept_id.uom_id",
        store=True,
        readonly=True,
    )
    notes = fields.Char()

    @api.constrains("input_id", "crew_id")
    def _check_resource(self):
        for yield_rec in self:
            if not yield_rec.input_id and not yield_rec.crew_id:
                raise ValidationError(_("A yield must reference an input or a crew."))
            if yield_rec.input_id and yield_rec.crew_id:
                raise ValidationError(_("A yield cannot reference both input and crew."))

    @api.constrains("concept_id", "catalog_version_id")
    def _check_concept_version(self):
        for yield_rec in self:
            if yield_rec.concept_id.catalog_version_id != yield_rec.catalog_version_id:
                raise ValidationError(_("Concept must belong to the same catalog version."))
