from odoo import api, fields, models


class ConstructionBudgetApuComponent(models.Model):
    _name = "construction.budget.apu.component"
    _description = "Construction APU Component"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    apu_id = fields.Many2one(
        "construction.budget.apu",
        string="APU",
        required=True,
        ondelete="cascade",
        index=True,
    )
    component_type = fields.Selection(
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
    )
    product_id = fields.Many2one("product.product", string="Product")
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        required=True,
        default=lambda self: self.env.ref(
            "uom.product_uom_unit", raise_if_not_found=False
        ),
    )
    quantity = fields.Float(default=1.0, digits="Product Unit of Measure")
    unit_cost = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    waste_percent = fields.Float(
        string="Waste %",
        digits=(16, 4),
        help="Percentage added to quantity (e.g. 5 for 5%).",
    )
    currency_id = fields.Many2one(
        related="apu_id.currency_id",
        store=True,
        readonly=True,
    )
    effective_quantity = fields.Float(
        string="Effective Qty",
        compute="_compute_effective_quantity",
        store=True,
        digits="Product Unit of Measure",
    )
    subtotal = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )
    notes = fields.Char()

    @api.depends("quantity", "waste_percent")
    def _compute_effective_quantity(self):
        for component in self:
            component.effective_quantity = component.quantity * (
                1.0 + (component.waste_percent or 0.0) / 100.0
            )

    @api.depends("effective_quantity", "unit_cost")
    def _compute_subtotal(self):
        for component in self:
            component.subtotal = component.effective_quantity * component.unit_cost

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price
