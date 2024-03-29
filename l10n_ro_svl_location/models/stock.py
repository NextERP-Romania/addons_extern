# Copyright (C) 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).


from odoo import api, fields, models
from odoo.tools import float_is_zero

import logging
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.depends("company_id", "location_id", "owner_id", "product_id", "quantity")
    def _compute_value(self):
        quants_with_loc = self.filtered(lambda q: q.location_id)
        for quant in quants_with_loc:
            super(
                StockQuant, quant.with_context(location_id=quant.location_id.id)
            )._compute_value()
        return super(StockQuant, self - quants_with_loc)._compute_value()


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    location_id = fields.Many2one(related="stock_move_id.location_id", store=True)
    location_dest_id = fields.Many2one(
        related="stock_move_id.location_dest_id", store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("stock_move_id"):
                move = self.env["stock.move"].browse(values["stock_move_id"])
                values["create_date"] = move.date
        records = super().create(vals_list)

        #check in models.py, in def _create method and the order is kept
        for vals, record in zip(vals_list, records):
            if 'location_id' in vals:
                record.location_id = vals['location_id']
            if 'location_dest_id' in vals:
                record.location_dest_id = vals['location_dest_id']
        return records


class StockMove(models.Model):
    _inherit = "stock.move"

    def _create_out_svl(self, forced_quantity=None):
        svls = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(location_id=move.location_id.id)
            svls |= super(StockMove, move)._create_out_svl(forced_quantity=forced_quantity)
        return svls

    def _create_internal_transfer_svl(self, forced_quantity=None):
        svls = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(location_id=move.location_id.id)
            svls |= super(StockMove, move)._create_internal_transfer_svl(forced_quantity=forced_quantity)
        return svls
        

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        for mv in moves:
            mv.location_id = mv.move_line_ids[0].location_id
            mv.location_dest_id = mv.move_line_ids[0].location_dest_id
        return moves        