from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext


class StockPicking(models.Model):
    _inherit = "stock.picking"
    is_rectified = fields.Boolean(default=False, readonly=True)

    def _create_payment(self, partner_id, amount, journal_id, payment_method_id):
        payment_obj = self.env["account.payment"]

        payment = payment_obj.create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner_id.id,
                "amount": amount,
                "payment_method_line_id": payment_method_id.id,
                "journal_id": journal_id.id,
                "date": fields.Date.today(),
                # "currency_id": journal_id.currency_id,
            }
        )
        payment.action_post()
        return payment

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if res:
            for picking in self:
                sale_order = picking.sale_id
                if sale_order and not picking.return_id:
                    if self.payment_state == "not_paid":
                        raise ValidationError(
                            _(
                                "This picking has not yet been paid, "
                                "please request payment at the checkout."
                            )
                        )

                    invoice = sale_order._create_invoices()
                    invoice.write({"payment_method": picking.payment_method.id})
                    if sale_order.note:
                        sale_order.invoice_ids.write({"narration": sale_order.note})
                        plain_text = html2plaintext(sale_order.note)

                        sale_order.invoice_ids.write(
                            {
                                "lines_info_additional": [
                                    (
                                        0,
                                        0,
                                        {
                                            "name": "Observaciones",
                                            "description": plain_text,
                                        },
                                    )
                                ]
                            }
                        )
                    if sale_order.lines_info_additional:
                        sale_order.invoice_ids.write(
                            {
                                "lines_info_additional": [
                                    (
                                        0,
                                        0,
                                        {
                                            "name": info.name,
                                            "description": info.description,
                                        },
                                    )
                                    for info in sale_order.lines_info_additional
                                ]
                            }
                        )
                    invoice.action_post()
                    sale_payment = sale_order.payment_ids
                    first_payment = sale_payment[0] if sale_payment else False
                    if first_payment:
                        payment = self._create_payment(
                            invoice.partner_id,
                            first_payment.difference,
                            first_payment.journal_id,
                            first_payment.payment_method_line_id,
                        )
                        invoice_receivable_accounts = invoice.line_ids.filtered(
                            lambda line: line.account_id.account_type
                            == "asset_receivable"
                        ).mapped("account_id")
                        for line in payment.move_id.line_ids:
                            if (
                                line.account_id in invoice_receivable_accounts
                                and line.balance < 0
                            ):
                                invoice.js_assign_outstanding_line(line.id)
                                break
                    invoice.with_delay().send_electronic_document()
                    invoice.info_message = "En cola de autorización"
                    invoice.state_send_document = "in_process"
                    picking.invoice_number = invoice.name
        return res
