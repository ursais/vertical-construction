from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionBudgetChapter(models.Model):
    _name = "construction.budget.chapter"
    _description = "Construction Budget Chapter"
    _order = "sequence, code, id"

    name = fields.Char(required=True)
    code = fields.Char(string="Chapter Code", index=True)
    sequence = fields.Integer(default=10)
    version_id = fields.Many2one(
        "construction.budget.version",
        string="Version",
        required=True,
        ondelete="cascade",
        index=True,
    )
    budget_id = fields.Many2one(
        related="version_id.budget_id",
        store=True,
        readonly=True,
    )
    parent_id = fields.Many2one(
        "construction.budget.chapter",
        string="Parent Chapter",
        ondelete="cascade",
        index=True,
    )
    budget_post_id = fields.Many2one(
        "account.budget.post",
        string="Budgetary Position",
        check_company=True,
        help="Accounting budget position used when syncing this chapter to "
        "crossovered budgets. Falls back to the construction budget default.",
    )
    child_ids = fields.One2many(
        "construction.budget.chapter",
        "parent_id",
        string="Sub-chapters",
    )
    line_ids = fields.One2many(
        "construction.budget.line",
        "chapter_id",
        string="Line Items",
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
    line_count = fields.Integer(compute="_compute_line_count")
    amount_total = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_amount_total",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("code", "name")
    def _compute_display_name(self):
        for chapter in self:
            if chapter.code:
                chapter.display_name = f"{chapter.code} - {chapter.name}"
            else:
                chapter.display_name = chapter.name

    @api.depends("line_ids")
    def _compute_line_count(self):
        for chapter in self:
            chapter.line_count = len(chapter.line_ids)

    @api.depends("line_ids.subtotal", "child_ids.amount_total")
    def _compute_amount_total(self):
        for chapter in self:
            direct = sum(chapter.line_ids.mapped("subtotal"))
            children = sum(chapter.child_ids.mapped("amount_total"))
            chapter.amount_total = direct + children

    def write(self, vals):
        for chapter in self:
            if chapter.version_id.is_frozen:
                raise UserError(
                    self.env._(
                        "Cannot modify chapters on frozen version '%(name)s'.",
                        name=chapter.version_id.display_name,
                    )
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_frozen_version(self):
        frozen_chapters = self.filtered(lambda chapter: chapter.version_id.is_frozen)
        if frozen_chapters:
            raise UserError(
                self.env._(
                    "Cannot delete chapters on frozen version '%(name)s'.",
                    name=frozen_chapters[0].version_id.display_name,
                )
            )

    def unlink(self):
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            version = self.env["construction.budget.version"].browse(
                vals.get("version_id")
            )
            if version.is_frozen:
                raise UserError(
                    self.env._(
                        "Cannot add chapters to frozen version '%(name)s'.",
                        name=version.display_name,
                    )
                )
        return super().create(vals_list)
