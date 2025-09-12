from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"
    is_rectified = fields.Boolean(default=False, readonly=True)

    sale_person_id = fields.Many2one(
        "res.users",
        string="Sale Person",
        compute="_compute_sale_person_id",
    )

    purchase_person_id = fields.Many2one(
        "res.users",
        string="Purchase Person",
        compute="_compute_purchase_person_id",
    )

    @api.depends("origin")
    def _compute_purchase_person_id(self):
        for picking in self:
            purchase_order = self.env["purchase.order"].search(
                [("name", "=", picking.origin)]
            )
            if purchase_order:
                picking.purchase_person_id = purchase_order.user_id
            else:
                picking.purchase_person_id = False

    @api.depends("origin")
    def _compute_sale_person_id(self):
        for picking in self:
            sale_order = self.env["sale.order"].search([("name", "=", picking.origin)])
            if sale_order:
                picking.sale_person_id = sale_order.user_id
            else:
                picking.sale_person_id = False

    def _create_pdc_payment(self, invoice, payment_line):
        payment_type = (
            "money_send" if invoice.move_type == "in_invoice" else "money_receive"
        )
        ctx = self.env.context
        wizard_vals = {
            "partner_name": ctx.get("default_partner_name", invoice.partner_id.id),
            "payment_amount": payment_line.amount,
            "invoice_ids": [(6, 0, ctx.get("default_invoice_ids", [invoice.id]))],
            "agent": payment_line.chq_agent,
            "payment_date": payment_line.chq_payment_date,
            "bank_details": payment_line.chq_bank_details.id,
            "due_date": payment_line.chq_due_date,
            "chq_refr": payment_line.chq_refr,
            "payment_type": payment_type,
            "journal_payment": payment_line.journal_id.id,
            "is_boolean": (
                True
                if invoice.env.company.pdc_settlement_order == "autopaid"
                else False
            ),
        }

        pdc_wizard = self.env["post.cheque.wizard"].create(wizard_vals)
        result = pdc_wizard.button_register()
        post_cheque = self.env["post.cheque"].browse(result.get("res_id"))
        post_cheque.write({"invoice_ids": [(6, 0, [invoice.id])]})
        post_cheque.with_context(last_deposit=False).deposting_action()
        pdc_move = self.env["account.move"].search(
            [
                "|",
                ("pd_cheque_id", "=", post_cheque.id),
                ("pd_reconciliation_id", "in", [post_cheque.id]),
            ]
        )

        return pdc_move

    def _create_payment(self, partner_id, payment_line):
        payment_obj = self.env["account.payment"]

        payment = payment_obj.create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner_id.id,
                "amount": payment_line.amount,
                "payment_method_line_id": payment_line.payment_method_line_id.id,
                "journal_id": payment_line.journal_id.id,
                "payment_card_id": payment_line.card_id.id,
                "global_reference": payment_line.reference,
                "voucher_reference": (
                    payment_line.reference if payment_line.card_id.id else False
                ),
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
                if picking.state != "assigned" and picking.picking_type_code == "outgoing":
                    raise ValidationError(_("The delivery has not been completed."))
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
                        for payment_line in first_payment.payment_line_ids:
                            if payment_line.chq_refr:
                                self._create_pdc_payment(invoice, payment_line)
                            else:
                                payment = self._create_payment(
                                    invoice.partner_id, payment_line
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


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    def action_assign(self):
        """Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.mapped("package_level_ids").filtered(
            lambda pl: pl.state == "draft" and not pl.move_ids
        )._generate_moves()
        self.filtered(lambda picking: picking.state == "draft").action_confirm()
        moves = self.move_ids.filtered(
            lambda move: move.state not in ("draft", "cancel", "done")
        ).sorted(
            key=lambda move: (
                -int(move.priority),
                not bool(move.date_deadline),
                move.date_deadline,
                move.date,
                move.id,
            )
        )
        moves._action_assign()
        return True
