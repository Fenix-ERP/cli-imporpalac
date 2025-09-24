from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = "stock.move"
    has_issue = fields.Boolean(default=False)
    issue_type = fields.Selection(
        [
            ("broken", "Broken"),
            ("damaged", "Damaged"),
            ("missing", "Missing"),
            ("expired", "Expired"),
            ("wrong_uom", "Wrong Unit of Measure"),
            ("wrong_location", "Wrong Location"),
            ("over_received", "Over Received"),
            ("under_received", "Under Received"),
            ("lot_missing", "Lot/Serial Missing"),
            ("quality_failed", "Quality Failed"),
        ],
        string="Issue",
    )
    issue_qty = fields.Float("Issue Quantity")
    issue_notes = fields.Text(help="Here you can write your issues")

    @api.model
    def get_issue_types(self):
        self = self.with_context(lang=self.env.user.lang or "en_US")
        allowed_states = ["broken", "damaged", "missing", "expired"]
        selection = dict(self._fields["issue_type"]._description_selection(self.env))
        types = allowed_states or selection.keys()
        return [
            {"value": val, "label": selection[val]} for val in types if val in selection
        ]

    @api.constrains("has_issue")
    def _check_has_issue(self):
        for record in self:
            if not record.has_issue:
                record.sudo().write(
                    {"issue_qty": 0, "issue_notes": False, "issue_type": False}
                )

    @api.constrains("has_issue", "issue_qty", "product_uom_qty", "product_uom")
    def _check_issue_qty(self):
        for record in self:
            if not record.has_issue:
                continue
            product_name = (
                record.product_id.display_name
                if record.product_id
                else _("Unknown Product")
            )
            precision = record.product_uom.rounding or 0.0001
            if float_compare(record.issue_qty, 0.0, precision_digits=precision) <= 0:
                raise ValidationError(
                    _(
                        "Issue Quantity for product '%s' must be greater than 0.",
                        product_name,
                    )
                )
            if (
                float_compare(
                    record.issue_qty, record.product_uom_qty, precision_digits=precision
                )
                > 0
            ):
                raise ValidationError(
                    _(
                        "Issue Quantity (%(issue_qty)s) for product '%(product)s' "
                        "cannot exceed demand (%(product_uom_qty)s)."
                    )
                    % {
                        "issue_qty": record.issue_qty,
                        "product": product_name,
                        "product_uom_qty": record.product_uom_qty,
                    }
                )
