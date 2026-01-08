# controllers/main.py
import json

from odoo import http
from odoo.http import request


class ZebraLabelController(http.Controller):
    @http.route(
        "/print/zebra_printer_name",
        type="http",
        auth="user",
        csrf=False,
    )
    def get_printer_name(self):
        qz_printer = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("qz.printer.zebra.name", default="")
        )

        return request.make_response(
            json.dumps(qz_printer), headers=[("Content-Type", "application/json")]
        )
