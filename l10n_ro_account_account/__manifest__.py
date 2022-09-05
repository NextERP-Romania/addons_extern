# Copyright 2022 NextERP Romania SRL
# License OPL-1.0 or later

{
    "name": "Romania - Account Account",
    "version": "14.0.1.0.0",
    "category": "Localisation",
    "author": "NextERP Romania SRL",
    "website": "https://nexterp.ro",
    "support": "odoo_apps@nexterp.ro",
    "summary": """Adapts Romanian Account""",
    "depends": ["account"],
    "data": [
        "views/account_move_views.xml",
        "report/invoice_report.xml",
    ],
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "license": "OPL-1",
}
