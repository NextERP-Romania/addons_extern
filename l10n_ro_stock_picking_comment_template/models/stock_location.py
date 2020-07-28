from odoo import models, fields, api, _


class stock_location(models.Model):
    _inherit = "stock.location"
    user_id = fields.Many2one('res.users', string='Manager')
