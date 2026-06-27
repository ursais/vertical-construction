from odoo import fields, models


class ConstructionCatalogConceptCategory(models.Model):
    _name = "construction.catalog.concept.category"
    _description = "Construction Concept Category"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(index=True)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one(
        "construction.catalog.concept.category",
        string="Parent Category",
        ondelete="restrict",
        index=True,
    )
    child_ids = fields.One2many(
        "construction.catalog.concept.category",
        "parent_id",
        string="Child Categories",
    )
    active = fields.Boolean(default=True)
