from odoo import fields, models
from odoo.exceptions import UserError


class ConstructionBudgetVersionApprove(models.TransientModel):
    _name = "construction.budget.version.approve"
    _description = "Approve Budget Version Wizard"

    version_id = fields.Many2one(
        "construction.budget.version",
        string="Version",
        required=True,
        readonly=True,
    )
    budget_id = fields.Many2one(related="version_id.budget_id", readonly=True)
    freeze_on_approve = fields.Boolean(
        string="Freeze on Approval",
        default=True,
        help="When checked, the version is frozen immediately after approval.",
    )
    notes = fields.Text(string="Approval Notes")

    def action_confirm(self):
        self.ensure_one()
        version = self.version_id
        if version.state not in ("draft", "submitted"):
            raise UserError(
                self.env._("Only draft or submitted versions can be approved.")
            )
        if version.state == "draft":
            version.action_submit()
        version.action_approve()
        if self.freeze_on_approve:
            version.action_freeze()
        if self.notes:
            version.message_post(body=self.notes)
        return {"type": "ir.actions.act_window_close"}


class ConstructionBudgetVersionReject(models.TransientModel):
    _name = "construction.budget.version.reject"
    _description = "Reject Budget Version Wizard"

    version_id = fields.Many2one(
        "construction.budget.version",
        string="Version",
        required=True,
        readonly=True,
    )
    rejection_reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        version = self.version_id
        if version.is_frozen:
            raise UserError(self.env._("Frozen versions cannot be rejected."))
        version.write(
            {
                "state": "rejected",
                "rejection_reason": self.rejection_reason,
            }
        )
        version.message_post(body=self.rejection_reason)
        return {"type": "ir.actions.act_window_close"}
