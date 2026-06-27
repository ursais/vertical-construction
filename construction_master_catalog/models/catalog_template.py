from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ConstructionCatalogTemplate(models.Model):
    _name = "construction.catalog.template"
    _description = "Construction APU Template (Plantilla)"
    _inherit = "construction.catalog.mixin.version"
    _order = "code, name, id"

    name = fields.Char(required=True)
    code = fields.Char(string="Template Code", required=True, index=True)
    concept_id = fields.Many2one(
        "construction.catalog.concept",
        string="Concept",
        required=True,
        domain="[('catalog_version_id', '=', catalog_version_id)]",
        index=True,
    )
    uom_id = fields.Many2one(
        related="concept_id.uom_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "construction.catalog.template.line",
        "template_id",
        string="Components",
    )
    unit_price = fields.Monetary(
        string="Unit Price",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_material = fields.Monetary(
        compute="_compute_amounts",
        store=True,
    )
    amount_labor = fields.Monetary(
        compute="_compute_amounts",
        store=True,
    )
    amount_equipment = fields.Monetary(
        compute="_compute_amounts",
        store=True,
    )
    amount_subcontract = fields.Monetary(
        compute="_compute_amounts",
        store=True,
    )
    amount_other = fields.Monetary(
        compute="_compute_amounts",
        store=True,
    )
    notes = fields.Html()

    _catalog_template_code_version_uniq = models.Constraint(
        "unique(code, catalog_version_id)",
        "Template code must be unique within a catalog version.",
    )

    @api.depends("line_ids.subtotal", "line_ids.input_type")
    def _compute_amounts(self):
        type_fields = {
            "material": "amount_material",
            "labor": "amount_labor",
            "equipment": "amount_equipment",
            "subcontract": "amount_subcontract",
            "other": "amount_other",
        }
        for template in self:
            totals = {field: 0.0 for field in type_fields.values()}
            for line in template.line_ids:
                field_name = type_fields.get(line.input_type, "amount_other")
                totals[field_name] += line.subtotal
            template.amount_material = totals["amount_material"]
            template.amount_labor = totals["amount_labor"]
            template.amount_equipment = totals["amount_equipment"]
            template.amount_subcontract = totals["amount_subcontract"]
            template.amount_other = totals["amount_other"]
            template.unit_price = sum(totals.values())


class ConstructionCatalogTemplateLine(models.Model):
    _name = "construction.catalog.template.line"
    _description = "Construction Template Component"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "construction.catalog.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    catalog_version_id = fields.Many2one(
        related="template_id.catalog_version_id",
        store=True,
        readonly=True,
    )
    version_state = fields.Selection(
        related="template_id.version_state",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    input_id = fields.Many2one(
        "construction.catalog.input",
        string="Input",
        required=True,
        domain="[('catalog_version_id', '=', catalog_version_id)]",
    )
    input_type = fields.Selection(related="input_id.input_type", store=True, readonly=True)
    quantity = fields.Float(default=1.0, digits="Product Unit of Measure")
    uom_id = fields.Many2one(related="input_id.uom_id", store=True, readonly=True)
    unit_cost = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="template_id.currency_id", store=True, readonly=True)
    waste_percent = fields.Float(digits=(16, 4))
    effective_quantity = fields.Float(
        compute="_compute_effective_quantity",
        store=True,
        digits="Product Unit of Measure",
    )
    subtotal = fields.Monetary(
        compute="_compute_subtotal",
        store=True,
        currency_field="currency_id",
    )
    notes = fields.Char()

    @api.depends("quantity", "waste_percent")
    def _compute_effective_quantity(self):
        for line in self:
            line.effective_quantity = line.quantity * (
                1.0 + (line.waste_percent or 0.0) / 100.0
            )

    @api.depends("effective_quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.effective_quantity * line.unit_cost

    @api.onchange("input_id")
    def _onchange_input_id(self):
        if self.input_id:
            self.unit_cost = self.input_id.unit_cost

    def write(self, vals):
        for line in self:
            if line.template_id.catalog_version_id.state == "closed":
                raise UserError(
                    _("Cannot modify records on closed catalog version '%(name)s'.")
                    % {"name": line.template_id.catalog_version_id.display_name}
                )
        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.template_id.catalog_version_id.state == "closed":
                raise UserError(
                    _("Cannot modify records on closed catalog version '%(name)s'.")
                    % {"name": line.template_id.catalog_version_id.display_name}
                )
        return super().unlink()
