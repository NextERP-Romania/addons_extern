# © 2013-2014 Nicolas Bessi (Camptocamp SA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Comments Templates",
    "summary": "Comments templates on documents",
    "version": "13.0.1.0.0",
    "category": "Reporting",
    "website": "https://github.com/OCA/reporting-engine",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/comment_view.xml",
        "views/res_partner_view.xml",
    ],
}
