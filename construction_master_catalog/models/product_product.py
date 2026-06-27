from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    construction_input_ids = fields.One2many(
        "construction.catalog.input",
        "product_id",
        string="Construction Inputs",
    )
    is_construction_input = fields.Boolean(
        string="Construction Input",
        help="Mark products that can be selected as construction catalog inputs.",
    )
