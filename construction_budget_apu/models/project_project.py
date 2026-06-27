from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    construction_budget_ids = fields.One2many(
        "construction.budget",
        "project_id",
        string="Construction Budgets",
    )
    construction_budget_count = fields.Integer(
        compute="_compute_construction_budget_count",
    )
    construction_budget_id = fields.Many2one(
        "construction.budget",
        string="Active Budget",
        compute="_compute_construction_budget_id",
        store=False,
    )

    def _compute_construction_budget_count(self):
        for project in self:
            project.construction_budget_count = len(project.construction_budget_ids)

    def _compute_construction_budget_id(self):
        for project in self:
            active = project.construction_budget_ids.filtered(
                lambda b: b.state == "active"
            )[:1]
            project.construction_budget_id = active

    def action_view_construction_budgets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Construction Budgets",
            "res_model": "construction.budget",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
                "default_analytic_account_id": self.account_id.id
                if hasattr(self, "account_id") and self.account_id
                else False,
            },
        }
