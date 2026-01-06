from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"
    _description = "Partner"

    @api.model
    def write(self, vals):
        if "identifier" in vals:
            raise ValidationError(
                _(
                    "Editing the customer's ID is not allowed. "
                    "Are you trying to create a new customer? "
                    "Try using the 'New' button."
                )
            )
        return super().write(vals)
