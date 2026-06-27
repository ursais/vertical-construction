from odoo import api, fields, models


class ConstructionBudgetCatalog(models.Model):
    _inherit = "construction.budget"

    catalog_version_id = fields.Many2one(
        "construction.catalog.version",
        string="Catalog Version",
        check_company=True,
        tracking=True,
        help="Master catalog version used to import concepts and APU templates.",
    )
    catalog_snapshot_id = fields.Many2one(
        "construction.catalog.snapshot",
        string="Catalog Snapshot",
        copy=False,
        readonly=True,
        check_company=True,
        help="Pinned catalog data for this budget after close or freeze.",
    )

    @api.model
    def _default_catalog_version_id(self):
        return self.env["construction.catalog.version"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("state", "=", "active"),
            ],
            limit=1,
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("catalog_version_id"):
                default_version = self._default_catalog_version_id()
                if default_version:
                    vals["catalog_version_id"] = default_version.id
        budgets = super().create(vals_list)
        return budgets

    def _ensure_catalog_snapshot(self):
        Snapshot = self.env["construction.catalog.snapshot"]
        for budget in self:
            if budget.catalog_snapshot_id:
                continue
            catalog_version = budget.catalog_version_id
            if not catalog_version:
                catalog_version = self.env["construction.catalog.version"].search(
                    [
                        ("company_id", "=", budget.company_id.id),
                        ("state", "in", ("active", "closed")),
                    ],
                    order="date_start desc",
                    limit=1,
                )
            if not catalog_version:
                continue
            snapshot = Snapshot.search(
                [
                    ("catalog_version_id", "=", catalog_version.id),
                    ("reference", "=", budget.name),
                ],
                limit=1,
            )
            if not snapshot:
                snapshot = Snapshot.create(
                    {
                        "name": f"{budget.name} / {catalog_version.name}",
                        "catalog_version_id": catalog_version.id,
                        "reference": budget.name,
                    }
                )
            budget.catalog_snapshot_id = snapshot

    def action_close(self):
        self._ensure_catalog_snapshot()
        return super().action_close()

    def action_view_catalog_snapshot(self):
        self.ensure_one()
        if not self.catalog_snapshot_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Catalog Snapshot"),
            "res_model": "construction.catalog.snapshot",
            "view_mode": "form",
            "res_id": self.catalog_snapshot_id.id,
        }
