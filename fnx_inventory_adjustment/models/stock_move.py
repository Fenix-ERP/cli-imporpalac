from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_src_account(self, accounts_data):
        account_id = self.env.context.get(
            "fnx_inventory_adjustment_counterpart_account_id"
        )
        if account_id and self.location_id.usage == "inventory":
            return account_id
        return super()._get_src_account(accounts_data)

    def _get_dest_account(self, accounts_data):
        account_id = self.env.context.get(
            "fnx_inventory_adjustment_counterpart_account_id"
        )
        if account_id and self.location_dest_id.usage == "inventory":
            return account_id
        return super()._get_dest_account(accounts_data)
