from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fnx_inventory_adjustment_gain_account_id = fields.Many2one(
        related="company_id.fnx_inventory_adjustment_gain_account_id",
        readonly=False,
        string="Inventory Adjustment Gain Account",
        domain=[("deprecated", "=", False), ("account_type", "!=", "view")],
    )

    fnx_inventory_adjustment_loss_account_id = fields.Many2one(
        related="company_id.fnx_inventory_adjustment_loss_account_id",
        readonly=False,
        string="Inventory Adjustment Loss Account",
        domain=[("deprecated", "=", False), ("account_type", "!=", "view")],
    )
