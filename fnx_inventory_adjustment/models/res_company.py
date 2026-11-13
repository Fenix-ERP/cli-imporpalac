from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    fnx_inventory_adjustment_gain_account_id = fields.Many2one(
        "account.account",
        string="Inventory Adjustment Gain Account",
        domain=[("deprecated", "=", False), ("account_type", "!=", "view")],
        help="Counterpart account used when an inventory adjustment increases "
        "the stock quantity or value.",
    )

    fnx_inventory_adjustment_loss_account_id = fields.Many2one(
        "account.account",
        string="Inventory Adjustment Loss Account",
        domain=[("deprecated", "=", False), ("account_type", "!=", "view")],
        help="Counterpart account used when an inventory adjustment decreases "
        "the stock quantity or value.",
    )

    def _get_inventory_adjustment_account(self, is_gain):
        self.ensure_one()
        field_name = (
            "fnx_inventory_adjustment_gain_account_id"
            if is_gain
            else "fnx_inventory_adjustment_loss_account_id"
        )
        label = (
            _("Inventory Adjustment Gain Account")
            if is_gain
            else _("Inventory Adjustment Loss Account")
        )
        account = getattr(self, field_name)
        if not account:
            raise UserError(
                _(
                    "Configure the '%(account)s' in the company settings before "
                    "processing the adjustment.",
                    account=label,
                )
            )
        if account.company_id != self:
            raise UserError(
                _(
                    "The '%(account)s' must belong to the same company as the "
                    "adjustment.",
                    account=label,
                )
            )
        return account
