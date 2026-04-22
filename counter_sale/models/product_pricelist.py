from odoo import _, models
from odoo.exceptions import UserError


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def unlink(self):
        xmlids = ["counter_sale.pricelist_special", "counter_sale.pricelist_wholesale"]
        protected_records = self.env["product.pricelist"]
        for xmlid in xmlids:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if rec:
                protected_records |= rec

        if protected_records & self:
            raise UserError(_("You cannot delete one of the protected Pricelists."))

        return super().unlink()
