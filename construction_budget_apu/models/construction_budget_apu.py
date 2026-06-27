from odoo import api, fields, models


class ConstructionBudgetApu(models.Model):
    _name = "construction.budget.apu"
    _description = "Construction Unit Price Analysis (APU)"
    _order = "name, id"

    name = fields.Char(required=True)
    reference = fields.Char()
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    component_ids = fields.One2many(
        "construction.budget.apu.component",
        "apu_id",
        string="Components",
    )
    line_ids = fields.One2many(
        "construction.budget.line",
        "apu_id",
        string="Budget Lines",
    )
    unit_price = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_material = fields.Monetary(
        string="Materials",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_labor = fields.Monetary(
        string="Labor",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_equipment = fields.Monetary(
        string="Equipment",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_subcontract = fields.Monetary(
        string="Subcontract",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_other = fields.Monetary(
        string="Other",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    notes = fields.Html()

    @api.depends("component_ids.subtotal", "component_ids.component_type")
    def _compute_amounts(self):
        type_fields = {
            "material": "amount_material",
            "labor": "amount_labor",
            "equipment": "amount_equipment",
            "subcontract": "amount_subcontract",
            "other": "amount_other",
        }
        for apu in self:
            totals = {field: 0.0 for field in type_fields.values()}
            for component in apu.component_ids:
                field_name = type_fields.get(component.component_type, "amount_other")
                totals[field_name] += component.subtotal
            apu.amount_material = totals["amount_material"]
            apu.amount_labor = totals["amount_labor"]
            apu.amount_equipment = totals["amount_equipment"]
            apu.amount_subcontract = totals["amount_subcontract"]
            apu.amount_other = totals["amount_other"]
            apu.unit_price = sum(totals.values())
