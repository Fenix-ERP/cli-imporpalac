from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()

        for pago in self:
            ref_text = pago.move_id.ref
            if ref_text:
                # Separamos por coma o espacio (por si acaso)
                nombres_facturas = [r.strip() for r in ref_text.replace(',', ' ').split() if r.strip()]
                for factura_name in nombres_facturas:
                    factura = self.env['account.move'].search([('name', '=', factura_name)], limit=1)
                    if factura and factura.invoice_origin:
                        orden = self.env['sale.order'].search([('name', '=', factura.invoice_origin)], limit=1)
                        if orden:
                            for despacho in orden.picking_ids:
                                if despacho.state != 'cancel':
                                    despacho.paid = True
        return res
