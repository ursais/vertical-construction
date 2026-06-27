from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ConstructionBudgetVersion(models.Model):
    _name = "construction.budget.version"
    _description = "Construction Budget Version"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "budget_id, version_number desc, id desc"

    name = fields.Char(required=True, tracking=True)
    budget_id = fields.Many2one(
        "construction.budget",
        string="Budget",
        required=True,
        ondelete="cascade",
        index=True,
    )
    version_number = fields.Integer(required=True, default=1, tracking=True)
    parent_version_id = fields.Many2one(
        "construction.budget.version",
        string="Parent Version",
        ondelete="set null",
        copy=False,
    )
    child_version_ids = fields.One2many(
        "construction.budget.version",
        "parent_version_id",
        string="Child Versions",
    )
    project_id = fields.Many2one(
        related="budget_id.project_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related="budget_id.partner_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="budget_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="budget_id.currency_id",
        store=True,
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        related="budget_id.analytic_account_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("frozen", "Frozen"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    is_frozen = fields.Boolean(
        string="Frozen",
        compute="_compute_is_frozen",
        store=True,
    )
    date_submitted = fields.Datetime(copy=False)
    date_approved = fields.Datetime(copy=False, tracking=True)
    date_frozen = fields.Datetime(copy=False, tracking=True)
    submitted_by_id = fields.Many2one("res.users", copy=False)
    approved_by_id = fields.Many2one("res.users", copy=False, tracking=True)
    frozen_by_id = fields.Many2one("res.users", copy=False, tracking=True)
    rejection_reason = fields.Text(copy=False)
    notes = fields.Html()
    crossovered_budget_id = fields.Many2one(
        "crossovered.budget",
        string="Accounting Budget",
        copy=False,
        ondelete="set null",
        tracking=True,
    )
    crossovered_budget_state = fields.Selection(
        related="crossovered_budget_id.state",
        string="Accounting Budget Status",
        readonly=True,
    )
    chapter_ids = fields.One2many(
        "construction.budget.chapter",
        "version_id",
        string="Chapters",
    )
    line_ids = fields.One2many(
        "construction.budget.line",
        "version_id",
        string="Line Items",
    )
    chapter_count = fields.Integer(compute="_compute_counts")
    line_count = fields.Integer(compute="_compute_counts")
    amount_total = fields.Monetary(
        string="Total Amount",
        currency_field="currency_id",
        compute="_compute_amount_total",
        store=True,
    )
    amount_material = fields.Monetary(
        string="Materials",
        currency_field="currency_id",
        compute="_compute_amount_breakdown",
        store=True,
    )
    amount_labor = fields.Monetary(
        string="Labor",
        currency_field="currency_id",
        compute="_compute_amount_breakdown",
        store=True,
    )
    amount_equipment = fields.Monetary(
        string="Equipment",
        currency_field="currency_id",
        compute="_compute_amount_breakdown",
        store=True,
    )
    amount_subcontract = fields.Monetary(
        string="Subcontract",
        currency_field="currency_id",
        compute="_compute_amount_breakdown",
        store=True,
    )
    amount_other = fields.Monetary(
        string="Other",
        currency_field="currency_id",
        compute="_compute_amount_breakdown",
        store=True,
    )

    _sql_constraints = [
        (
            "budget_version_number_uniq",
            "unique(budget_id, version_number)",
            "Version number must be unique per budget.",
        ),
    ]

    @api.depends("state")
    def _compute_is_frozen(self):
        for version in self:
            version.is_frozen = version.state == "frozen"

    @api.depends("chapter_ids", "line_ids")
    def _compute_counts(self):
        for version in self:
            version.chapter_count = len(version.chapter_ids)
            version.line_count = len(version.line_ids)

    @api.depends("line_ids.subtotal")
    def _compute_amount_total(self):
        for version in self:
            version.amount_total = sum(version.line_ids.mapped("subtotal"))

    @api.depends(
        "line_ids.apu_id.amount_material",
        "line_ids.apu_id.amount_labor",
        "line_ids.apu_id.amount_equipment",
        "line_ids.apu_id.amount_subcontract",
        "line_ids.apu_id.amount_other",
    )
    def _compute_amount_breakdown(self):
        for version in self:
            apus = version.line_ids.mapped("apu_id")
            version.amount_material = sum(apus.mapped("amount_material"))
            version.amount_labor = sum(apus.mapped("amount_labor"))
            version.amount_equipment = sum(apus.mapped("amount_equipment"))
            version.amount_subcontract = sum(apus.mapped("amount_subcontract"))
            version.amount_other = sum(apus.mapped("amount_other"))

    def _check_editable(self):
        self.ensure_one()
        if self.is_frozen:
            raise UserError(
                self.env._(
                    "Version '%(name)s' is frozen and cannot be modified.",
                    name=self.display_name,
                )
            )

    def copy_structure_to(self, target_version):
        """Duplicate chapters, lines and APUs into another version."""
        self.ensure_one()
        target_version.ensure_one()
        chapter_map = {}
        for chapter in self.chapter_ids.sorted("sequence"):
            new_chapter = chapter.copy(
                {
                    "version_id": target_version.id,
                    "parent_id": chapter_map.get(chapter.parent_id.id),
                }
            )
            chapter_map[chapter.id] = new_chapter.id
        for line in self.line_ids.sorted("sequence"):
            line.copy(
                {
                    "version_id": target_version.id,
                    "chapter_id": chapter_map.get(line.chapter_id.id),
                }
            )

    def _get_sync_dates(self):
        self.ensure_one()
        budget = self.budget_id
        date_from = budget.date_start or fields.Date.context_today(self)
        date_to = budget.date_end or date_from
        if date_from > date_to:
            raise ValidationError(self.env._("End date must be after start date."))
        return date_from, date_to

    def _get_budget_post_for_line(self, line):
        self.ensure_one()
        post = line.chapter_id.budget_post_id or self.budget_id.default_budget_post_id
        if not post:
            raise UserError(
                self.env._(
                    "Configure a default budgetary position on budget '%(budget)s' "
                    "or on chapter '%(chapter)s' before syncing.",
                    budget=self.budget_id.display_name,
                    chapter=line.chapter_id.display_name,
                )
            )
        return post

    def _prepare_crossovered_budget_vals(self):
        self.ensure_one()
        date_from, date_to = self._get_sync_dates()
        budget = self.budget_id
        return {
            "name": f"{budget.name} / {self.name}",
            "date_from": date_from,
            "date_to": date_to,
            "company_id": budget.company_id.id,
            "construction_budget_id": budget.id,
            "construction_budget_version_id": self.id,
        }

    def _aggregate_planned_amounts(self):
        self.ensure_one()
        aggregates = {}
        for line in self.line_ids:
            post = self._get_budget_post_for_line(line)
            key = post.id
            aggregates[key] = aggregates.get(key, 0.0) + line.subtotal
        return aggregates

    def _sync_crossovered_budget(self):
        CrossoveredBudget = self.env["crossovered.budget"]
        BudgetPost = self.env["account.budget.post"]
        for version in self:
            if not version.line_ids:
                raise UserError(
                    self.env._(
                        "Cannot sync version '%(name)s' without line items.",
                        name=version.display_name,
                    )
                )
            aggregates = version._aggregate_planned_amounts()
            date_from, date_to = version._get_sync_dates()
            budget = version.budget_id
            line_commands = []
            for post_id, amount in aggregates.items():
                post = BudgetPost.browse(post_id)
                line_commands.append(
                    (
                        0,
                        0,
                        {
                            "general_budget_id": post.id,
                            "analytic_account_id": budget.analytic_account_id.id,
                            "date_from": date_from,
                            "date_to": date_to,
                            "planned_amount": -abs(amount),
                        },
                    )
                )
            if version.crossovered_budget_id:
                crossovered = version.crossovered_budget_id
                crossovered.write(
                    {
                        "name": version._prepare_crossovered_budget_vals()["name"],
                        "date_from": date_from,
                        "date_to": date_to,
                    }
                )
                crossovered.crossovered_budget_line_ids.unlink()
                crossovered.write({"crossovered_budget_line_ids": line_commands})
            else:
                vals = version._prepare_crossovered_budget_vals()
                vals["crossovered_budget_line_ids"] = line_commands
                crossovered = CrossoveredBudget.create(vals)
                version.crossovered_budget_id = crossovered
        return True

    def _advance_crossovered_budget_state(self, target_state):
        for version in self:
            crossovered = version.crossovered_budget_id
            if not crossovered:
                continue
            if target_state == "confirm" and crossovered.state == "draft":
                crossovered.action_budget_confirm()
            elif target_state == "validate":
                if crossovered.state == "draft":
                    crossovered.action_budget_confirm()
                if crossovered.state == "confirm":
                    crossovered.action_budget_validate()
            elif target_state == "done":
                version._advance_crossovered_budget_state("validate")
                if crossovered.state == "validate":
                    crossovered.action_budget_done()

    def action_open_crossovered_budget(self):
        self.ensure_one()
        if not self.crossovered_budget_id:
            raise UserError(
                self.env._("No accounting budget linked to this version yet.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Accounting Budget"),
            "res_model": "crossovered.budget",
            "view_mode": "form",
            "res_id": self.crossovered_budget_id.id,
        }

    def action_submit(self):
        for version in self:
            if not version.line_ids:
                raise UserError(
                    self.env._("Cannot submit a version without line items.")
                )
            version.write(
                {
                    "state": "submitted",
                    "date_submitted": fields.Datetime.now(),
                    "submitted_by_id": self.env.user.id,
                }
            )

    def action_approve(self):
        for version in self:
            if version.state not in ("submitted", "draft"):
                raise UserError(
                    self.env._("Only draft or submitted versions can be approved.")
                )
            version._sync_crossovered_budget()
            version.write(
                {
                    "state": "approved",
                    "date_approved": fields.Datetime.now(),
                    "approved_by_id": self.env.user.id,
                }
            )
            version.budget_id.approved_version_id = version
            version._advance_crossovered_budget_state("confirm")

    def action_freeze(self):
        for version in self:
            if version.state != "approved":
                raise UserError(self.env._("Only approved versions can be frozen."))
            version._sync_crossovered_budget()
            version.write(
                {
                    "state": "frozen",
                    "date_frozen": fields.Datetime.now(),
                    "frozen_by_id": self.env.user.id,
                }
            )
            version.budget_id.approved_version_id = version
            version._advance_crossovered_budget_state("validate")

    def action_reject(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Reject Version"),
            "res_model": "construction.budget.version.reject",
            "view_mode": "form",
            "target": "new",
            "context": {"default_version_id": self.id},
        }

    def action_reset_draft(self):
        for version in self:
            if version.is_frozen:
                raise UserError(self.env._("Frozen versions cannot be reset to draft."))
            version.write({"state": "draft", "rejection_reason": False})

    def action_open_approve_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Approve Version"),
            "res_model": "construction.budget.version.approve",
            "view_mode": "form",
            "target": "new",
            "context": {"default_version_id": self.id},
        }

    def write(self, vals):
        locked_fields = {
            "chapter_ids",
            "line_ids",
            "name",
            "notes",
        }
        if locked_fields.intersection(vals.keys()):
            for version in self:
                if version.is_frozen:
                    raise UserError(
                        self.env._(
                            "Frozen version '%(name)s' cannot be edited.",
                            name=version.display_name,
                        )
                    )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_frozen(self):
        frozen_versions = self.filtered("is_frozen")
        if frozen_versions:
            raise UserError(self.env._("Frozen versions cannot be deleted."))

    def unlink(self):
        return super().unlink()

    def get_line_snapshot(self):
        """Return a dict keyed by chapter_code + line_code for comparisons."""
        self.ensure_one()
        snapshot = {}
        for line in self.line_ids:
            key = (line.chapter_id.code or "", line.code or line.id)
            snapshot[key] = {
                "line": line,
                "chapter_name": line.chapter_id.name,
                "line_name": line.name,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "subtotal": line.subtotal,
            }
        return snapshot
