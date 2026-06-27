from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionBudgetLine(models.Model):
    _name = "construction.budget.line"
    _description = "Construction Budget Line Item"
    _order = "sequence, code, id"

    name = fields.Char(string="Description", required=True)
    code = fields.Char(string="Item Code", index=True)
    sequence = fields.Integer(default=10)
    version_id = fields.Many2one(
        "construction.budget.version",
        string="Version",
        required=True,
        ondelete="cascade",
        index=True,
    )
    chapter_id = fields.Many2one(
        "construction.budget.chapter",
        string="Chapter",
        required=True,
        ondelete="cascade",
        domain="[('version_id', '=', version_id)]",
        index=True,
    )
    budget_id = fields.Many2one(
        related="version_id.budget_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="version_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="version_id.currency_id",
        store=True,
        readonly=True,
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
    unit_price = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_unit_price",
        store=True,
        readonly=False,
    )
    subtotal = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )
    apu_id = fields.Many2one(
        "construction.budget.apu",
        string="APU",
        ondelete="restrict",
        copy=True,
    )
    apu_mode = fields.Boolean(
        string="Use APU",
        default=True,
        help="When enabled, unit price is computed from the APU breakdown.",
    )
    notes = fields.Text()
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("code", "name")
    def _compute_display_name(self):
        for line in self:
            if line.code:
                line.display_name = f"{line.code} - {line.name}"
            else:
                line.display_name = line.name

    @api.depends("apu_id.unit_price", "apu_mode")
    def _compute_unit_price(self):
        for line in self:
            if line.apu_mode and line.apu_id:
                line.unit_price = line.apu_id.unit_price
            elif not line.apu_mode:
                line.unit_price = line.unit_price or 0.0

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.model_create_multi
    def create(self, vals_list):
        apu_model = self.env["construction.budget.apu"]
        for vals in vals_list:
            version = self.env["construction.budget.version"].browse(
                vals.get("version_id")
            )
            if version.is_frozen:
                raise UserError(
                    self.env._(
                        "Cannot add lines to frozen version '%(name)s'.",
                        name=version.display_name,
                    )
                )
            if vals.get("apu_mode", True) and not vals.get("apu_id"):
                apu = apu_model.create({"name": vals.get("name", self.env._("APU"))})
                vals["apu_id"] = apu.id
        return super().create(vals_list)

    def write(self, vals):
        for line in self:
            if line.version_id.is_frozen:
                raise UserError(
                    self.env._(
                        "Cannot modify lines on frozen version '%(name)s'.",
                        name=line.version_id.display_name,
                    )
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_frozen_version(self):
        frozen_lines = self.filtered(lambda line: line.version_id.is_frozen)
        if frozen_lines:
            raise UserError(
                self.env._(
                    "Cannot delete lines on frozen version '%(name)s'.",
                    name=frozen_lines[0].version_id.display_name,
                )
            )

    def unlink(self):
        apus = self.mapped("apu_id")
        res = super().unlink()
        orphan_apus = apus.filtered(lambda apu: not apu.line_ids)
        orphan_apus.unlink()
        return res

    def action_open_apu(self):
        self.ensure_one()
        if not self.apu_id:
            self.apu_id = self.env["construction.budget.apu"].create(
                {"name": self.name}
            )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Unit Price Analysis"),
            "res_model": "construction.budget.apu",
            "view_mode": "form",
            "res_id": self.apu_id.id,
        }

    def copy(self, default=None):
        default = dict(default or {})
        new_line = super().copy(default)
        if self.apu_id:
            new_apu = self.apu_id.copy()
            new_line.apu_id = new_apu
        return new_line
