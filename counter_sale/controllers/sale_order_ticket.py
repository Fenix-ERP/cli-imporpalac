# controllers/main.py
from odoo import http
from odoo.http import request


class TicketController(http.Controller):
    @http.route(
        "/print/ticket_html/<int:order_id>/dispatch",
        type="http",
        auth="user",
        csrf=False,
    )
    def render_ticket_template(self, order_id):
        order = request.env["sale.order"].browse(order_id)
        IrActionsReport = request.env["ir.actions.report"]
        html = IrActionsReport._render_qweb_html(
            "sale_order_ticket.action_report_ticket_dispatch", order.ids
        )[0]
        return request.make_response(html)

    @http.route(
        "/print/ticket_html/<int:order_id>/cash_register",
        type="http",
        auth="user",
        csrf=False,
    )
    def render_ticket_cash_template(self, order_id):
        order = request.env["sale.order"].browse(order_id)
        IrActionsReport = request.env["ir.actions.report"]
        html = IrActionsReport._render_qweb_html(
            "sale_order_ticket.action_report_ticket_cash", order.ids
        )[0]
        return request.make_response(html)
