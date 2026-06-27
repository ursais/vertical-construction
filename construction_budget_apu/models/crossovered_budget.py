from odoo import fields, models


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    construction_budget_id = fields.Many2one(
        "construction.budget",
        string="Construction Budget",
        ondelete="set null",
        index=True,
    )
    construction_budget_version_id = fields.Many2one(
        "construction.budget.version",
        string="Construction Budget Version",
        ondelete="set null",
        index=True,
    )


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    construction_chapter_id = fields.Many2one(
        "construction.budget.chapter",
        string="Construction Chapter",
        ondelete="set null",
    )
