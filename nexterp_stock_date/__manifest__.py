# Copyright (C) 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

{
    "name": "Stock Processing Date",
    "version": "15.0.1.0.1",
    "depends": ["sale_stock", "purchase_stock"],
    "description": """Stock Processing Date, Remove Update Qty from Product View""",
    "data": [
        "views/product_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_quant_views.xml",
    ],
    "author": "NextERP Romania",
    "website": "https://nexterp.ro",
    "support": "contact@nexterp.ro",
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "license": "OPL-1",
}
