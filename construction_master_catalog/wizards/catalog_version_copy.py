from odoo import _, fields, models
from odoo.exceptions import UserError


class ConstructionCatalogVersionCopy(models.TransientModel):
    _name = "construction.catalog.version.copy"
    _description = "Copy Catalog to New Version"

    source_version_id = fields.Many2one(
        "construction.catalog.version",
        string="Source Version",
        required=True,
        readonly=True,
    )
    name = fields.Char(required=True)
    code = fields.Char(string="Code", required=True)
    date_start = fields.Date(string="Valid From", required=True)

    def action_copy(self):
        self.ensure_one()
        if self.source_version_id.state == "draft":
            raise UserError(_("Copy from an active or closed version, not a draft."))
        new_version = self.source_version_id.copy_catalog_to(
            {
                "name": self.name,
                "code": self.code,
                "date_start": self.date_start,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Catalog Version"),
            "res_model": "construction.catalog.version",
            "view_mode": "form",
            "res_id": new_version.id,
        }
