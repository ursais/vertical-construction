from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionBudgetVersionCompare(models.TransientModel):
    _name = "construction.budget.version.compare"
    _description = "Compare Budget Versions"

    budget_id = fields.Many2one(
        "construction.budget",
        string="Budget",
        required=True,
    )
    version_a_id = fields.Many2one(
        "construction.budget.version",
        string="Base Version",
        required=True,
        domain="[('budget_id', '=', budget_id)]",
    )
    version_b_id = fields.Many2one(
        "construction.budget.version",
        string="Compare Version",
        required=True,
        domain="[('budget_id', '=', budget_id)]",
    )
    currency_id = fields.Many2one(related="budget_id.currency_id", readonly=True)
    line_ids = fields.One2many(
        "construction.budget.version.compare.line",
        "compare_id",
        string="Comparison Lines",
    )
    amount_total_a = fields.Monetary(
        related="version_a_id.amount_total",
        currency_field="currency_id",
    )
    amount_total_b = fields.Monetary(
        related="version_b_id.amount_total",
        currency_field="currency_id",
    )
    amount_delta = fields.Monetary(
        string="Total Delta",
        currency_field="currency_id",
        compute="_compute_amount_delta",
    )
    amount_delta_percent = fields.Float(
        string="Delta %",
        compute="_compute_amount_delta",
        digits=(16, 2),
    )

    @api.depends("version_a_id.amount_total", "version_b_id.amount_total")
    def _compute_amount_delta(self):
        for wizard in self:
            base = wizard.version_a_id.amount_total or 0.0
            compare = wizard.version_b_id.amount_total or 0.0
            wizard.amount_delta = compare - base
            wizard.amount_delta_percent = (
                ((compare - base) / base * 100.0) if base else 0.0
            )

    @api.onchange("version_a_id", "version_b_id")
    def _onchange_versions(self):
        if self.version_a_id and self.version_b_id:
            self._generate_comparison_lines()

    def action_generate(self):
        for wizard in self:
            wizard._generate_comparison_lines()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def _generate_comparison_lines(self):
        self.ensure_one()
        if not self.version_a_id or not self.version_b_id:
            return
        if self.version_a_id == self.version_b_id:
            raise UserError(self.env._("Please select two different versions."))
        snapshot_a = self.version_a_id.get_line_snapshot()
        snapshot_b = self.version_b_id.get_line_snapshot()
        all_keys = sorted(set(snapshot_a.keys()) | set(snapshot_b.keys()))
        lines = [(5, 0, 0)]
        for key in all_keys:
            data_a = snapshot_a.get(key)
            data_b = snapshot_b.get(key)
            qty_a = data_a["quantity"] if data_a else 0.0
            qty_b = data_b["quantity"] if data_b else 0.0
            price_a = data_a["unit_price"] if data_a else 0.0
            price_b = data_b["unit_price"] if data_b else 0.0
            sub_a = data_a["subtotal"] if data_a else 0.0
            sub_b = data_b["subtotal"] if data_b else 0.0
            chapter_code, line_code = key
            if data_a:
                chapter_name = data_a["chapter_name"]
                line_name = data_a["line_name"]
            elif data_b:
                chapter_name = data_b["chapter_name"]
                line_name = data_b["line_name"]
            else:
                chapter_name = line_name = ""
            change_type = "unchanged"
            if data_a and not data_b:
                change_type = "removed"
            elif data_b and not data_a:
                change_type = "added"
            elif sub_a != sub_b or qty_a != qty_b or price_a != price_b:
                change_type = "modified"
            lines.append(
                (
                    0,
                    0,
                    {
                        "chapter_code": chapter_code,
                        "line_code": str(line_code),
                        "chapter_name": chapter_name,
                        "line_name": line_name,
                        "quantity_a": qty_a,
                        "quantity_b": qty_b,
                        "unit_price_a": price_a,
                        "unit_price_b": price_b,
                        "subtotal_a": sub_a,
                        "subtotal_b": sub_b,
                        "subtotal_delta": sub_b - sub_a,
                        "change_type": change_type,
                    },
                )
            )
        self.line_ids = lines


class ConstructionBudgetVersionCompareLine(models.TransientModel):
    _name = "construction.budget.version.compare.line"
    _description = "Compare Budget Version Line"
    _order = "chapter_code, line_code, id"

    compare_id = fields.Many2one(
        "construction.budget.version.compare",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(related="compare_id.currency_id", readonly=True)
    chapter_code = fields.Char()
    line_code = fields.Char()
    chapter_name = fields.Char()
    line_name = fields.Char()
    quantity_a = fields.Float(digits="Product Unit of Measure")
    quantity_b = fields.Float(digits="Product Unit of Measure")
    unit_price_a = fields.Monetary(currency_field="currency_id")
    unit_price_b = fields.Monetary(currency_field="currency_id")
    subtotal_a = fields.Monetary(currency_field="currency_id")
    subtotal_b = fields.Monetary(currency_field="currency_id")
    subtotal_delta = fields.Monetary(currency_field="currency_id")
    change_type = fields.Selection(
        [
            ("added", "Added"),
            ("removed", "Removed"),
            ("modified", "Modified"),
            ("unchanged", "Unchanged"),
        ],
        default="unchanged",
    )
