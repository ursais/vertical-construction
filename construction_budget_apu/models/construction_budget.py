from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionBudget(models.Model):
    _name = "construction.budget"
    _description = "Construction Budget"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env._("New"),
        tracking=True,
    )
    code = fields.Char(tracking=True)
    description = fields.Text()
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="project_id.partner_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        required=True,
        check_company=True,
        tracking=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="set null",
        copy=False,
    )
    default_budget_post_id = fields.Many2one(
        "account.budget.post",
        string="Default Budgetary Position",
        check_company=True,
        tracking=True,
        help="Used when syncing approved versions to accounting budgets "
        "and when a chapter has no specific budgetary position.",
    )
    crossovered_budget_ids = fields.One2many(
        "crossovered.budget",
        "construction_budget_id",
        string="Accounting Budgets",
    )
    crossovered_budget_count = fields.Integer(
        compute="_compute_crossovered_budget_count",
    )
    version_ids = fields.One2many(
        "construction.budget.version",
        "budget_id",
        string="Versions",
    )
    version_count = fields.Integer(compute="_compute_version_count")
    current_version_id = fields.Many2one(
        "construction.budget.version",
        string="Current Version",
        copy=False,
        ondelete="set null",
        domain="[('budget_id', '=', id)]",
        tracking=True,
    )
    approved_version_id = fields.Many2one(
        "construction.budget.version",
        string="Approved Version",
        copy=False,
        ondelete="set null",
        domain="[('budget_id', '=', id), ('state', 'in', ('approved', 'frozen'))]",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    amount_total = fields.Monetary(
        string="Total Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_approved = fields.Monetary(
        string="Approved Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    active = fields.Boolean(default=True)

    @api.depends("version_ids", "current_version_id", "approved_version_id")
    def _compute_version_count(self):
        for budget in self:
            budget.version_count = len(budget.version_ids)

    @api.depends("crossovered_budget_ids")
    def _compute_crossovered_budget_count(self):
        for budget in self:
            budget.crossovered_budget_count = len(budget.crossovered_budget_ids)

    @api.depends(
        "current_version_id.amount_total",
        "approved_version_id.amount_total",
    )
    def _compute_amounts(self):
        for budget in self:
            budget.amount_total = budget.current_version_id.amount_total or 0.0
            budget.amount_approved = budget.approved_version_id.amount_total or 0.0

    @api.model_create_multi
    def create(self, vals_list):
        new_label = self.env._("New")
        for vals in vals_list:
            if vals.get("name", new_label) == new_label:
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("construction.budget")
                    or new_label
                )
        return super().create(vals_list)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for budget in self:
            if (
                budget.date_start
                and budget.date_end
                and budget.date_start > budget.date_end
            ):
                raise ValidationError(self.env._("End date must be after start date."))

    def action_activate(self):
        self.write({"state": "active"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def action_create_version(self):
        self.ensure_one()
        last_number = max(self.version_ids.mapped("version_number") or [0])
        version = self.env["construction.budget.version"].create(
            {
                "budget_id": self.id,
                "version_number": last_number + 1,
                "name": self.env._("Version %s", last_number + 1),
                "parent_version_id": self.current_version_id.id
                if self.current_version_id
                else False,
            }
        )
        if self.current_version_id:
            self.current_version_id.copy_structure_to(version)
        self.current_version_id = version
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Budget Version"),
            "res_model": "construction.budget.version",
            "view_mode": "form",
            "res_id": version.id,
        }

    def action_view_versions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Budget Versions"),
            "res_model": "construction.budget.version",
            "view_mode": "list,form",
            "domain": [("budget_id", "=", self.id)],
            "context": {"default_budget_id": self.id},
        }

    def action_view_crossovered_budgets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Accounting Budgets"),
            "res_model": "crossovered.budget",
            "view_mode": "list,form",
            "domain": [("construction_budget_id", "=", self.id)],
            "context": {"default_construction_budget_id": self.id},
        }

    def action_compare_versions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Compare Versions"),
            "res_model": "construction.budget.version.compare",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_budget_id": self.id,
                "default_version_a_id": self.approved_version_id.id
                if self.approved_version_id
                else self.current_version_id.id,
                "default_version_b_id": self.current_version_id.id,
            },
        }
