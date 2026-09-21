{
    "name": "Fénix Inventory Adjustment",
    "version": "17.0.0.0.1",
    "depends": ["devolutions", "stock_account", "web_notify", "pf_branch_base"],
    "author": "FenixERP",
    "category": "Inventory",
    "license": "GPL-3",
    "data": [
        "data/sequence.xml",
        "security/ir.model.access.csv",
        "views/fnx_inventory_adjustment_views.xml",
        "views/fnx_inventory_adjustment_report_wizard_views.xml",
    ],
    "external_dependencies": {
        "python": [
            "openpyxl",
        ],
    },
}
