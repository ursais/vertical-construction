from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ConstructionCatalogCrew(models.Model):
    _name = "construction.catalog.crew"
    _description = "Construction Crew (Cuadrilla)"
    _inherit = "construction.catalog.mixin.version"
    _order = "code, name, id"

    name = fields.Char(required=True)
    code = fields.Char(string="Crew Code", required=True, index=True)
    line_ids = fields.One2many(
        "construction.catalog.crew.line",
        "crew_id",
        string="Crew Members",
    )
    daily_cost = fields.Monetary(
        string="Daily Cost",
        currency_field="currency_id",
        compute="_compute_daily_cost",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _catalog_crew_code_version_uniq = models.Constraint(
        "unique(code, catalog_version_id)",
        "Crew code must be unique within a catalog version.",
    )

    @api.depends("line_ids.subtotal")
    def _compute_daily_cost(self):
        for crew in self:
            crew.daily_cost = sum(crew.line_ids.mapped("subtotal"))


class ConstructionCatalogCrewLine(models.Model):
    _name = "construction.catalog.crew.line"
    _description = "Construction Crew Line"
    _order = "sequence, id"

    crew_id = fields.Many2one(
        "construction.catalog.crew",
        string="Crew",
        required=True,
        ondelete="cascade",
        index=True,
    )
    catalog_version_id = fields.Many2one(
        related="crew_id.catalog_version_id",
        store=True,
        readonly=True,
    )
    version_state = fields.Selection(
        related="crew_id.version_state",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    input_id = fields.Many2one(
        "construction.catalog.input",
        string="Labor Input",
        required=True,
        domain="[('catalog_version_id', '=', catalog_version_id), ('input_type', '=', 'labor')]",
    )
    role = fields.Char(string="Role")
    quantity = fields.Float(
        string="Workers",
        default=1.0,
        digits="Product Unit of Measure",
    )
    unit_cost = fields.Monetary(
        string="Unit Cost",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="crew_id.currency_id",
        store=True,
        readonly=True,
    )
    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost

    @api.onchange("input_id")
    def _onchange_input_id(self):
        if self.input_id:
            self.unit_cost = self.input_id.unit_cost
            self.role = self.input_id.name

    def write(self, vals):
        for line in self:
            if line.crew_id.catalog_version_id.state == "closed":
                raise UserError(
                    _("Cannot modify records on closed catalog version '%(name)s'.")
                    % {"name": line.crew_id.catalog_version_id.display_name}
                )
        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.crew_id.catalog_version_id.state == "closed":
                raise UserError(
                    _("Cannot modify records on closed catalog version '%(name)s'.")
                    % {"name": line.crew_id.catalog_version_id.display_name}
                )
        return super().unlink()
