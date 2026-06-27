from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ConstructionCatalogVersion(models.Model):
    _name = "construction.catalog.version"
    _description = "Construction Catalog Version (Vigencia)"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True)
    code = fields.Char(string="Code", index=True)
    date_start = fields.Date(string="Valid From", required=True, index=True)
    date_end = fields.Date(string="Valid To", index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    previous_version_id = fields.Many2one(
        "construction.catalog.version",
        string="Previous Version",
        readonly=True,
        copy=False,
    )
    notes = fields.Text()
    concept_count = fields.Integer(compute="_compute_counts")
    input_count = fields.Integer(compute="_compute_counts")
    template_count = fields.Integer(compute="_compute_counts")
    snapshot_count = fields.Integer(compute="_compute_counts")
    concept_ids = fields.One2many("construction.catalog.concept", "catalog_version_id")
    input_ids = fields.One2many("construction.catalog.input", "catalog_version_id")
    uom_ids = fields.One2many("construction.catalog.uom", "catalog_version_id")
    yield_ids = fields.One2many("construction.catalog.yield", "catalog_version_id")
    crew_ids = fields.One2many("construction.catalog.crew", "catalog_version_id")
    template_ids = fields.One2many("construction.catalog.template", "catalog_version_id")
    snapshot_ids = fields.One2many("construction.catalog.snapshot", "catalog_version_id")

    _catalog_version_code_company_uniq = models.Constraint(
        "unique(code, company_id)",
        "Catalog version code must be unique per company.",
    )

    @api.depends("concept_ids", "input_ids", "template_ids", "snapshot_ids")
    def _compute_counts(self):
        for version in self:
            version.concept_count = len(version.concept_ids)
            version.input_count = len(version.input_ids)
            version.template_count = len(version.template_ids)
            version.snapshot_count = len(version.snapshot_ids)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for version in self:
            if version.date_end and version.date_start > version.date_end:
                raise ValidationError(_("Valid From must be before Valid To."))

    @api.constrains("state", "date_start", "date_end", "company_id")
    def _check_single_active(self):
        for version in self.filtered(lambda v: v.state == "active"):
            overlap = self.search(
                [
                    ("id", "!=", version.id),
                    ("company_id", "=", version.company_id.id),
                    ("state", "=", "active"),
                ],
                limit=1,
            )
            if overlap:
                raise ValidationError(
                    _("Only one active catalog version is allowed per company.")
                )

    def action_activate(self):
        for version in self:
            if version.state != "draft":
                raise UserError(_("Only draft versions can be activated."))
            previous = self.search(
                [
                    ("company_id", "=", version.company_id.id),
                    ("state", "=", "active"),
                ],
                limit=1,
            )
            if previous:
                previous.write({"state": "closed", "date_end": version.date_start})
            version.write({"state": "active"})
        return True

    def action_close(self):
        for version in self:
            if version.state != "active":
                raise UserError(_("Only active versions can be closed."))
            version.state = "closed"
        return True

    def action_set_draft(self):
        for version in self:
            if version.state == "closed":
                raise UserError(_("Closed catalog versions cannot be reopened."))
            version.state = "draft"
        return True

    def action_create_snapshot(self):
        self.ensure_one()
        if self.state != "closed":
            raise UserError(_("Create a snapshot only from a closed catalog version."))
        snapshot = self.env["construction.catalog.snapshot"].create(
            {
                "name": self.name,
                "catalog_version_id": self.id,
                "reference": self.code,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Catalog Snapshot"),
            "res_model": "construction.catalog.snapshot",
            "view_mode": "form",
            "res_id": snapshot.id,
        }

    def action_open_copy_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Copy to New Version"),
            "res_model": "construction.catalog.version.copy",
            "view_mode": "form",
            "target": "new",
            "context": {"default_source_version_id": self.id},
        }

    def copy_catalog_to(self, new_version_vals):
        """Duplicate all catalog records into a new draft version."""
        self.ensure_one()
        new_version = self.create(
            {
                **new_version_vals,
                "previous_version_id": self.id,
                "state": "draft",
                "company_id": self.company_id.id,
            }
        )
        concept_map = {}
        for concept in self.concept_ids:
            concept_map[concept.id] = concept.copy(
                {"catalog_version_id": new_version.id}
            ).id
        input_map = {}
        for catalog_input in self.input_ids:
            input_map[catalog_input.id] = catalog_input.copy(
                {"catalog_version_id": new_version.id}
            ).id
        for uom in self.uom_ids:
            uom.copy({"catalog_version_id": new_version.id})
        crew_map = {}
        crew_line_model = self.env["construction.catalog.crew.line"]
        for crew in self.crew_ids:
            new_crew = self.env["construction.catalog.crew"].create(
                {
                    "name": crew.name,
                    "code": crew.code,
                    "catalog_version_id": new_version.id,
                    "notes": crew.notes,
                    "active": crew.active,
                }
            )
            crew_map[crew.id] = new_crew.id
            for line in crew.line_ids:
                crew_line_model.create(
                    {
                        "crew_id": new_crew.id,
                        "sequence": line.sequence,
                        "input_id": input_map.get(line.input_id.id),
                        "role": line.role,
                        "quantity": line.quantity,
                        "unit_cost": line.unit_cost,
                    }
                )
        yield_model = self.env["construction.catalog.yield"]
        for yield_rec in self.yield_ids:
            yield_model.create(
                {
                    "catalog_version_id": new_version.id,
                    "concept_id": concept_map.get(yield_rec.concept_id.id),
                    "input_id": input_map.get(yield_rec.input_id.id)
                    if yield_rec.input_id
                    else False,
                    "crew_id": crew_map.get(yield_rec.crew_id.id)
                    if yield_rec.crew_id
                    else False,
                    "yield_quantity": yield_rec.yield_quantity,
                    "resource_quantity": yield_rec.resource_quantity,
                    "notes": yield_rec.notes,
                }
            )
        template_model = self.env["construction.catalog.template"]
        template_line_model = self.env["construction.catalog.template.line"]
        for template in self.template_ids:
            new_template = template_model.create(
                {
                    "name": template.name,
                    "code": template.code,
                    "catalog_version_id": new_version.id,
                    "concept_id": concept_map.get(template.concept_id.id),
                    "notes": template.notes,
                }
            )
            for line in template.line_ids:
                mapped_input = input_map.get(line.input_id.id)
                if not mapped_input:
                    continue
                template_line_model.create(
                    {
                        "template_id": new_template.id,
                        "sequence": line.sequence,
                        "input_id": mapped_input,
                        "quantity": line.quantity,
                        "waste_percent": line.waste_percent,
                        "unit_cost": line.unit_cost,
                        "notes": line.notes,
                    }
                )
        return new_version

    def action_view_concepts(self):
        self.ensure_one()
        return self._action_view_related("construction.catalog.concept", "concept_ids")

    def action_view_inputs(self):
        self.ensure_one()
        return self._action_view_related("construction.catalog.input", "input_ids")

    def action_view_templates(self):
        self.ensure_one()
        return self._action_view_related("construction.catalog.template", "template_ids")

    def action_view_snapshots(self):
        self.ensure_one()
        return self._action_view_related("construction.catalog.snapshot", "snapshot_ids")

    def _action_view_related(self, model, field_name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self._fields[field_name].string,
            "res_model": model,
            "view_mode": "list,form",
            "domain": [("catalog_version_id", "=", self.id)],
            "context": {"default_catalog_version_id": self.id},
        }
