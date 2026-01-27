from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"
    is_inter_company = fields.Boolean(
        compute="_compute_is_inter_company_sale", store=False
    )

    @api.depends("partner_id")
    def _compute_is_inter_company_sale(self):
        internal_partners = (
            self.env["res.company"].sudo().search([]).mapped("partner_id")
        )
        for order in self:
            order.is_inter_company = order.partner_id in internal_partners

    rectified_order_id = fields.Many2one(
        "sale.order", string="Rectified Sale Order", readonly=True
    )
    expired = fields.Boolean(readonly=False)

    product_pricelist_domain = fields.Char(
        compute="_compute_product_pricelist_domain",
    )

    @api.depends(
        "partner_id",
        "partner_id.property_product_pricelist",
        "company_id.product_pricelist_ids_default",
    )
    def _compute_product_pricelist_domain(self):
        allowed_pricelist = self.company_id.product_pricelist_ids_default
        allowed_ids = allowed_pricelist.ids if allowed_pricelist else []
        for order in self:
            if order.partner_id:
                allowed_ids.append(order.partner_id.property_product_pricelist.id)
            domain = [("id", "in", allowed_ids)]
            order.product_pricelist_domain = str(domain)

    @api.onchange(
        "partner_id",
        "partner_id.property_product_pricelist",
        "company_id.product_pricelist_ids_default",
    )
    def _onchange_pricelist_id_force_first(self):
        allowed = self.company_id.product_pricelist_ids_default
        if self.partner_id and self.partner_id.property_product_pricelist:
            allowed |= self.partner_id.property_product_pricelist
        if allowed:
            self.pricelist_id = allowed.sorted("id")[0]

    @api.onchange("pricelist_id")
    def _onchange_pricelist_id_show_update_prices(self):
        self._recompute_prices()
        res = super()._onchange_pricelist_id_show_update_prices()
        self.show_update_pricelist = False
        return res

    @api.model
    def action_print_ticket(self, order_id):
        order = self.browse(order_id)
        if order.state != "sale":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Invalid status"),
                    "message": _("The order must be in Confirmed state to print."),
                    "sticky": False,
                    "type": "danger",
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "print_sale_order",
            "params": {
                "order_id": order.id,
            },
        }

    def action_confirm(self):
        self = self.sudo()
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        if self.state == "draft":
            return res
        self.add_or_update_lines_info(
            [
                {"name": _("Order"), "description": self.name},
                {
                    "name": _("Payment Method"),
                    "description": self.payment_method.name,
                },
            ]
        )
        rectified_related_pickings = self.rectified_order_id.picking_ids
        related_pickings = self.picking_ids
        for old_picking, new_picking in zip(
            rectified_related_pickings, related_pickings
        ):
            new_picking.is_rectified = True
            for old_move in old_picking.move_ids:
                new_move = new_picking.move_ids.filtered(
                    lambda m: m.product_id == old_move.product_id
                )
                if new_move:
                    new_move.rectified_product_uom_qty = (
                        old_move.rectified_product_uom_qty
                    )
                    new_move.rectified_quantity = old_move.rectified_quantity
        journal_payment_ids = self.warehouse_id.payment_method_ids.filtered(
            lambda line: line.payment_type_id.id == self.payment_method.id
        ).journal_payment_ids
        journal_payment_id = journal_payment_ids[0] if journal_payment_ids else False
        if not journal_payment_id and self.payment_method.code != "credit":
            raise ValidationError(
                _(
                    "There is no payment journal for %(payment_method)s "
                    "in warehouse %(warehouse)s, please assign it."
                )
                % {
                    "payment_method": self.payment_method.display_name,
                    "warehouse": self.warehouse_id.display_name,
                }
            )
        if self.payment_method.code != "credit":
            rectified_amount = 0
            if self.rectified_order_id:
                sale_order_payment = (
                    self.env["sale.order.payment"]
                    .sudo()
                    .search([("order_id", "=", self.rectified_order_id.id)])
                )
                if sale_order_payment.state == "cancel":
                    rectified_amount = 0
                else:
                    rectified_amount = self.rectified_order_id.amount_total
            journal_payment_domain = (
                "[('id', 'in', %s)]" % journal_payment_ids.ids or []
            )
            self.sudo().env["sale.order.payment"].create(
                {
                    "client_id": self.partner_id.id,
                    "order_id": self.id,
                    "date_order": self.date_order,
                    "amount": self.amount_total,
                    "rectified_order_id": self.rectified_order_id.id,
                    "rectified_date_order": self.rectified_order_id.date_order,
                    "rectified_amount": rectified_amount,
                    "journal_id": journal_payment_id.id,
                    "journal_domain": journal_payment_domain,
                    "payment_method": self.payment_method.id,
                    "state": "draft",
                    "company_id": self.company_id.id,
                    "pf_branch_id": self.pf_branch_id.id,
                }
            )
        else:
            related_pickings.sudo().write({"payment_state": "credit"})
        return res

    def action_cancel(self):
        self.ensure_one()
        if self.invoice_count > 0:
            raise UserError(
                _("This order already has an invoice assigned and cannot be cancelled.")
            )
        dissable_locked = self.env.context.get("force_dissable_locked", False)
        if dissable_locked:
            self.sudo().locked = False
        res = super(SaleOrder, self).action_cancel()
        if dissable_locked:
            self.sudo().locked = True
        return res

    def action_expire_quotations(self, hours=48):
        expiration_time = datetime.now() - timedelta(hours=hours)
        expired_orders = self.sudo().search(
            [
                ("state", "=", "draft"),
                ("create_date", "<=", expiration_time),
            ]
        )
        expired_orders.sudo().write({"state": "cancel", "expired": True})


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_pricelist_domain = fields.Char(
        related="order_id.product_pricelist_domain",
    )
