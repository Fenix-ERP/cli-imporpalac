from odoo import _, fields, models
from odoo.exceptions import UserError

class ElectronicVoucherUpdate(models.Model):
    _inherit = "account.evoucher"
    _description = "Electronic Voucher"


    def update_costs_action(self):
        """Update costs in the linked purchase order after validations"""
        self.ensure_one()

        if not self.purchase_order_id:
            raise UserError(_("This e-voucher is not linked to any purchase order."))
        
        if self.vendor_id != self.purchase_order_id.partner_id:
            raise UserError(_(
                "The vendor %s doesn't match the purchase order's vendor %s."
            ) % (self.vendor_id.name, self.purchase_order_id.partner_id.name))
        
        if self.purchase_order_id.picking_ids.filtered(lambda p: p.state == 'done'):
            raise UserError(_("You have already validated the receipt of a purchase order."))

        non_homologated_products = []
        for line in self.lines_ride:
            if not line.product_id:
                product_name = line.description or line.code or "Unknown product"
                non_homologated_products.append(product_name)

        if non_homologated_products:
            products_list = "\n- ".join(non_homologated_products)
            raise UserError(_(
                "The following products are not approved in the system:\n- %s\n"
                "Please homologate products before updating costs."
            ) % products_list)

        updated_lines = 0
        for line in self.lines_ride:
            if line.product_id:
                po_line = self.purchase_order_id.order_line.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if po_line:
                    po_line.write({
                        'price_unit': line.price_unit,
                        'discount': line.discount,
                        'product_qty': line.quantity,
                    })
                    updated_lines += 1

        if not updated_lines:
            raise UserError(_("No matching products found in the purchase order to update."))

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Costs updated successfully!'),
                'type': 'rainbow_man',
            }
        }