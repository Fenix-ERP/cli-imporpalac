from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def write(self, vals):
        if (
            "identifier" in vals
            or "vat" in vals
            and not self.env.context.get("allow_edit_vat", False)
        ):
            if not self.env.user.has_group(
                "counter_sale.group_counter_sale_identifier_editor"
            ):
                raise ValidationError(
                    _(
                        "Editing the customer's ID is not allowed. "
                        "Are you trying to create a new customer? "
                        "Try using the 'New' button."
                    )
                )
        return super().write(vals)
