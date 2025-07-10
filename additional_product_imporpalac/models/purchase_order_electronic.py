from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrderElectronic(models.Model):
    _inherit = "purchase.order"

    evoucher_ids = fields.Many2one(
        comodel_name="account.evoucher",
        string="Electronic Voucher",
        help="Select an electronic receipt from the existing list",
        domain="[('state', '=', 'pending')]",
    )

    def action_update_costs(self):
        """Update costs based on the selected electronic voucher,
        only if it complies with the validations and the products are approved."""
        self.ensure_one()

        if not self.evoucher_ids:
            raise UserError(_("No hay comprobantes electrónicos seleccionados."))

        non_homologated_products = []

        for evoucher in self.evoucher_ids:
            if evoucher.vendor_id != self.partner_id:
                raise UserError(
                    _(
                        f"The voucher {evoucher.key_access} does not belong to the supplier {self.partner_id.name}."
                    )
                )

            if evoucher.invoice_id:
                raise UserError(
                    _(
                        f"The voucher {evoucher.key_access} is already linked to the invoice {evoucher.invoice_id.name}."
                    )
                )

            if evoucher.purchase_order_id and evoucher.purchase_order_id != self:
                raise UserError(
                    _(
                        f"The voucher {evoucher.key_access} is already linked to the purchase order {evoucher.purchase_order_id.name}."
                    )
                )

            for line in evoucher.lines_ride:
                if not line.product_id:
                    product_name = line.description or line.code
                    non_homologated_products.append(product_name)

        if non_homologated_products:
            products_list = "\n- ".join(non_homologated_products)
            raise UserError(
                _(
                    "The following products are not approved in the system:\n- %s\n"
                    "Please homologate products before updating costs."
                )
                % products_list
            )

        for evoucher in self.evoucher_ids:
            for line in evoucher.lines_ride:
                po_line = self.order_line.filtered(
                    lambda l: l.product_id == line.product_id
                )

                if po_line:
                    po_line.write(
                        {
                            "price_unit": line.price_unit,
                            "discount": line.discount,
                            "product_qty": line.quantity,
                        }
                    )

        return {
            "effect": {
                "fadeout": "slow",
                "message": "Correctly updated costs for approved products.",
                "type": "rainbow_man",
            }
        }
