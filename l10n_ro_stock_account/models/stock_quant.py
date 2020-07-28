# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    price_unit = fields.Float(
        'Unit Price', compute='_compute_price_unit', store=True,
        help="Technical field used to record the product cost set by the user "
             "during a inventory confirmation (when costing method used is "
             "'average price' or 'real'). Value given in company currency "
             "and in product uom.", copy=False)

    @api.depends('value', 'quantity')
    def _compute_price_unit(self):
        """ For standard and AVCO valuation, compute the current accounting
        valuation of the quants by multiplying the quantity by
        the standard price. Instead for FIFO, use the quantity times the
        average cost (valuation layers are not manage by location so the
        average cost is the same for all location and the valuation field is
        a estimation more than a real value).
        """
        for quant in self:
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.quantity:
                quant.price_unit = 0
            else:
                quant.price_unit = quant.value / quant.quantity