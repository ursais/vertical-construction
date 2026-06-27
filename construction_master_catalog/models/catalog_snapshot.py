from odoo import fields, models


class ConstructionCatalogSnapshot(models.Model):
    _name = "construction.catalog.snapshot"
    _description = "Construction Catalog Snapshot"
    _order = "snapshot_date desc, id desc"

    name = fields.Char(required=True)
    catalog_version_id = fields.Many2one(
        "construction.catalog.version",
        string="Catalog Version",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        related="catalog_version_id.company_id",
        store=True,
        readonly=True,
    )
    reference = fields.Char(
        string="External Reference",
        help="Project, budget or work order reference using this snapshot.",
        index=True,
    )
    snapshot_date = fields.Datetime(
        string="Snapshot Date",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    date_start = fields.Date(related="catalog_version_id.date_start", store=True)
    date_end = fields.Date(related="catalog_version_id.date_end", store=True)
    notes = fields.Text()

    _catalog_snapshot_version_ref_uniq = models.Constraint(
        "unique(catalog_version_id, reference)",
        "Only one snapshot per catalog version and reference is allowed.",
    )
