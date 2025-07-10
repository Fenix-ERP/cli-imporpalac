from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"
    picker_user_id = fields.Many2one("res.users", string="Picker User", readonly=True)
    is_owner_picker_user = fields.Boolean(compute="_compute_is_owner_user")
    is_rectified = fields.Boolean(default=False, readonly=True)

    def _compute_is_owner_user(self):
        for picking in self:
            picking.is_owner_picker_user = picking.picker_user_id.id == self.env.user.id

    def action_claim_picking(self):
        for picking in self:
            picking.picker_user_id = self.env.user.id
            picking.state = "confirmed"

    def action_confirm_picking(self):
        for picking in self:
            picking.user_id = self.env.user.id
            picking.state = "assigned"

    def _create_payment(self, partner_id, amount, journal_id):
        payment_obj = self.env["account.payment"]

        payment = payment_obj.create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner_id.id,
                "amount": amount,
                # "payment_method_id": payment_method_id,
                "journal_id": journal_id.id,
                "date": fields.Date.today(),
                # "currency_id": journal_id.currency_id,
                "ref": _("Pago xd"),
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
                    if not self.paid:
                        raise ValidationError(
                            _(
                                "This picking has not yet been paid, "
                                "please request payment at the checkout."
                            )
                        )

                    invoice = sale_order._create_invoices()
                    invoice.write({"payment_method": picking.payment_method.id})
                    invoice.action_post()
                    sale_payment = sale_order.payment_ids
                    first_payment = sale_payment[0] if sale_payment else False
                    if not first_payment:
                        raise ValidationError(
                            _(
                                "This picking has not yet been paid, "
                                "please request payment at the checkout."
                            )
                        )
                    payment = self._create_payment(
                        invoice.partner_id,
                        first_payment.difference,
                        first_payment.journal_id,
                    )
                    invoice_receivable_accounts = invoice.line_ids.filtered(
                        lambda line: line.account_id.account_type == "asset_receivable"
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
