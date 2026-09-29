from odoo import fields, models


class FnxAdjustmentReason(models.Model):
    _name = "fnx.adjustment.reason"
    _description = "FnxAdjustmentReason"

    name = fields.Char(
        required=True,
    )
