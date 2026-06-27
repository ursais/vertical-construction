from odoo import api, fields, models


class ConstructionCatalogInput(models.Model):
    _name = "construction.catalog.input"
    _description = "Construction Master Input (Insumo)"
    _inherit = "construction.catalog.mixin.version"
    _order = "code, name, id"

    name = fields.Char(required=True)
    code = fields.Char(string="Input Code", required=True, index=True)
    input_type = fields.Selection(
        [
            ("material", "Material"),
            ("labor", "Labor"),
            ("equipment", "Equipment"),
            ("subcontract", "Subcontract"),
            ("other", "Other"),
        ],
        string="Type",
        required=True,
        default="material",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        index=True,
        help="Linked product for stock and purchase integration.",
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    unit_cost = fields.Monetary(
        string="Unit Cost",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    supplier_id = fields.Many2one(
        "res.partner",
        string="Preferred Supplier",
        domain="[('supplier_rank', '>', 0)]",
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _catalog_input_code_version_uniq = models.Constraint(
        "unique(code, catalog_version_id)",
        "Input code must be unique within a catalog version.",
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for catalog_input in self:
            if catalog_input.code:
                catalog_input.display_name = f"{catalog_input.code} - {catalog_input.name}"
            else:
                catalog_input.display_name = catalog_input.name

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price
