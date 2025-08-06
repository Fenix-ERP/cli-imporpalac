# controllers/main.py
import json

from odoo import http
from odoo.http import request


class TicketController(http.Controller):
    @http.route(
        "/print/ticket_html/<int:order_id>/dispatch",
        type="http",
        auth="user",
        csrf=False,
    )
    def render_ticket_dispatch_template(self, order_id):
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

    @http.route(
        "/print/imporpalac_printers",
        type="http",
        auth="user",
        csrf=False,
    )
    def get_printer_name(self):
        cash_printer_name = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("qz.printer.cash.name", default="")
        )
        dispatch_printer_name = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("qz.printer.dispatch.name", default="")
        )
        response_data = {
            "cash_printer": cash_printer_name,
            "dispatch_printer": dispatch_printer_name,
        }

        return request.make_response(
            json.dumps(response_data), headers=[("Content-Type", "application/json")]
        )
