from odoo import models


class Location(models.Model):
    _inherit = "stock.location"

    def should_bypass_reservation(self):
        if self.usage == "supplier":
            return False
        res = super(Location, self).should_bypass_reservation()
        return res
