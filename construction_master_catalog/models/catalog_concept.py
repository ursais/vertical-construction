from odoo import api, fields, models


class ConstructionCatalogConcept(models.Model):
    _name = "construction.catalog.concept"
    _description = "Construction Master Concept"
    _inherit = "construction.catalog.mixin.version"
    _order = "code, name, id"

    name = fields.Char(string="Description", required=True)
    code = fields.Char(string="Concept Code", required=True, index=True)
    category_id = fields.Many2one(
        "construction.catalog.concept.category",
        string="Category",
        ondelete="restrict",
        index=True,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        help="Optional product used for billing or stock integration.",
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _catalog_concept_code_version_uniq = models.Constraint(
        "unique(code, catalog_version_id)",
        "Concept code must be unique within a catalog version.",
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for concept in self:
            if concept.code:
                concept.display_name = f"{concept.code} - {concept.name}"
            else:
                concept.display_name = concept.name

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.uom_id = self.product_id.uom_id
