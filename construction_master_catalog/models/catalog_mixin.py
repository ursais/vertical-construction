from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ConstructionCatalogVersionMixin(models.AbstractModel):
    _name = "construction.catalog.mixin.version"
    _description = "Catalog Version Protection Mixin"

    catalog_version_id = fields.Many2one(
        "construction.catalog.version",
        string="Catalog Version",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="catalog_version_id.company_id",
        store=True,
        readonly=True,
    )
    version_state = fields.Selection(
        related="catalog_version_id.state",
        store=True,
        readonly=True,
    )

    def _check_version_not_closed(self):
        closed = self.filtered(lambda r: r.catalog_version_id.state == "closed")
        if closed:
            raise UserError(
                _("Cannot modify records on closed catalog version '%(name)s'.")
                % {"name": closed[0].catalog_version_id.display_name}
            )

    def write(self, vals):
        self._check_version_not_closed()
        return super().write(vals)

    def unlink(self):
        self._check_version_not_closed()
        return super().unlink()
