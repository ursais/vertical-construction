from odoo import fields, models


class ConstructionCatalogUom(models.Model):
    _name = "construction.catalog.uom"
    _description = "Construction Unit Catalog"
    _inherit = "construction.catalog.mixin.version"
    _order = "code, name, id"

    name = fields.Char(required=True)
    code = fields.Char(string="Unit Code", required=True, index=True)
    uom_id = fields.Many2one(
        "uom.uom",
        string="Odoo Unit of Measure",
        required=True,
        ondelete="restrict",
    )
    uom_category_id = fields.Many2one(
        related="uom_id.category_id",
        store=True,
        readonly=True,
    )
    factor = fields.Float(
        string="Conversion Factor",
        default=1.0,
        digits=(16, 6),
        help="Factor to convert from this construction unit to the Odoo UoM.",
    )
    notes = fields.Char()
    active = fields.Boolean(default=True)

    _catalog_uom_code_version_uniq = models.Constraint(
        "unique(code, catalog_version_id)",
        "Unit code must be unique within a catalog version.",
    )
