# controllers/main.py
import json

from odoo import http
from odoo.http import request


class TreeViewRefreshController(http.Controller):
    @http.route(
        "/tree_view_refresh/allowed_models",
        type="http",
        auth="user",
        csrf=False,
    )
    def get_allowed_models(self):
        allowed_models = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("refresh_tree_view_allowed_models", default="")
        )
        allowed_list = [m.strip() for m in allowed_models.split(",") if m.strip()]
        return request.make_response(
            json.dumps(allowed_list), headers=[("Content-Type", "application/json")]
        )
