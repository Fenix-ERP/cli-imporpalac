from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        default=lambda self: self.env.ref(
            "payment_type.payment_type_cash", raise_if_not_found=False
        ),
    )

    credit = fields.Monetary(
        related="partner_id.credit",
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.payment_method = self.partner_id.payment_method

    @api.onchange("pricelist_id", "payment_method")
    def _onchange_pricelist_or_payment_method(self):
        """Validate the price list and consumer payment method
        When selecting a card as the payment method, credit card
        """
        if self.pricelist_id:
            # card_pricelist = self.env['product.pricelist'].browse(6)
            card_pricelist = self.env["product.pricelist"].search(
                [("name", "ilike", "Tarjeta"), ("active", "=", True)], limit=1
            )

            if self.pricelist_id == card_pricelist:
                card_payment = self.env["payment.type"].search(
                    [("name", "ilike", "tarjeta")], limit=1
                )

                if card_payment and self.payment_method != card_payment:
                    self.payment_method = card_payment

        if self.partner_id and self.partner_id.id == 7:
            cash_payment = self.env.ref(
                "payment_type.payment_type_cash", raise_if_not_found=False
            )
            cash_pricelist = self.env["product.pricelist"].browse(1)

            if self.payment_method and self.payment_method != cash_payment:
                self.payment_method = cash_payment
                raise ValidationError(
                    _("For end consumers, only cash payment is allowed.")
                )

            if self.pricelist_id and self.pricelist_id != cash_pricelist:
                self.pricelist_id = cash_pricelist
                raise ValidationError(
                    _("For end consumers, only cash payment is allowed.")
                )

    def action_confirm(self):

        for order in self:
            identifier = order.partner_id.is_end_consumer
            if identifier:
                if order.amount_total > order.company_id.max_amount_final_consumer:
                    raise ValidationError(
                        _("Exceeds the maximum value for end consumers")
                    )

            if order.warehouse_id and order.payment_method:

                payment_method = order.warehouse_id.payment_method_ids.filtered(
                    lambda pm: pm.payment_type_id == order.payment_method
                )
                if payment_method:
                    for journal_payment_id in payment_method.journal_payment_ids:
                        journal = journal_payment_id
                        method_lines = journal.inbound_payment_method_line_ids
                        has_no_account = method_lines.filtered(
                            lambda method: not method.payment_account_id
                        )
                        if has_no_account:
                            raise ValidationError(
                                _(
                                    "The 'Pending receipt accounts' field is empty for the payment method: "
                                    "%s\n\n"
                                    "Please correct the configuration before proceeding."
                                )
                                % journal.display_name
                            )

            insufficient_products = []
            for line in order.order_line:
                if line.product_id.type == "product":
                    available_qty = 0.0
                    if line.internal_location_id:
                        location = line.internal_location_id
                        quants = (
                            self.sudo()
                            .env["stock.quant"]
                            .search(
                                [
                                    ("product_id", "=", line.product_id.id),
                                    ("location_id", "=", location.id),
                                ]
                            )
                        )
                        physical_qty = sum(quants.mapped("quantity")) - sum(
                            quants.mapped("reserved_quantity")
                        )
                        moves = (
                            self.sudo()
                            .env["stock.move"]
                            .search(
                                [
                                    ("product_id", "=", line.product_id.id),
                                    ("state", "in", ("confirmed", "assigned")),
                                    ("internal_location_id", "=", location.id),
                                    ("picking_type_id.code", "=", "outgoing"),
                                ]
                            )
                        )
                        committed_qty = 0.0
                        for m in moves:
                            done_qty = sum(m.move_line_ids.mapped("quantity"))
                            committed_qty += m.product_uom_qty - done_qty
                        available_qty = physical_qty - committed_qty
                    else:
                        available_qty = (
                            line.product_id.qty_available - line.product_id.outgoing_qty
                        )

                    if line.product_uom_qty > available_qty:
                        location_info = ""
                        if line.internal_location_id:
                            location_info = (
                                f" en {line.internal_location_id.display_name}"
                            )

                        insufficient_products.append(
                            _(
                                "%(product)s (Solicitado: %(requested)s, Disponible: %(available)s%(location)s)"
                            )
                            % {
                                "product": line.product_id.display_name,
                                "requested": line.product_uom_qty,
                                "available": available_qty,
                                "location": location_info,
                            }
                        )

            if insufficient_products:
                raise ValidationError(
                    _("There is insufficient stock for the following products:\n%s")
                    % "\n".join(insufficient_products)
                )
        res = super().action_confirm()
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ["done", "cancel"]
            )
            pickings.sudo().write({"payment_method": order.payment_method})
        return res

    def _create_invoices(self, grouped=False, final=False):
        invoices = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final)

        for invoice in invoices:
            related_pickings = self.picking_ids.filtered(lambda p: p.state == "done")
            if related_pickings:
                warehouse = related_pickings[0].picking_type_id.warehouse_id
                if warehouse and warehouse.journal_id:
                    invoice.journal_id = warehouse.journal_id
        return invoices


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    image_1920 = fields.Image(related="product_id.image_1920", readonly=True)
