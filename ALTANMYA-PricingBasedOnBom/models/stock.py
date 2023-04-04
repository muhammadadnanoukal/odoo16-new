import logging
from collections import defaultdict, namedtuple


from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, html_escape
from odoo.tools.misc import split_every

_logger = logging.getLogger(__name__)
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import float_compare, OrderedSet

class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_explode(self, bom_ids=False):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
        # all grouped in the same picking.
        moves_ids_to_return = OrderedSet()
        moves_ids_to_unlink = OrderedSet()
        phantom_moves_vals_list = []
        for move in self:
            if not move.picking_type_id or (move.production_id and move.production_id.product_id == move.product_id):
                moves_ids_to_return.add(move.id)
                continue
            bom = self.env['mrp.bom'].sudo()._bom_find(move.product_id, company_id=move.company_id.id,
                                                       bom_type=['phantom', 'assembled'], bom_ids=bom_ids)[move.product_id]
            if not bom:
                moves_ids_to_return.add(move.id)
                continue

            if bom[0]:
                factor = 0
                if move.picking_id.immediate_transfer:
                    for bo in bom:
                        factor += move.product_uom._compute_quantity(move.quantity_done, bo.product_uom_id) / bo.product_qty
                else:
                    for bo in bom:
                        factor += move.product_uom._compute_quantity(move.product_uom_qty, bo.product_uom_id) / bo.product_qty
                boms, lines = bo.sudo().explode(move.product_id, factor, picking_type=bo.picking_type_id, bom_ids=bom_ids)
                for bom_line, line_data in lines:
                    if move.picking_id.immediate_transfer:
                        phantom_moves_vals_list += move._generate_move_phantom(bom_line, 0, line_data['qty'])
                    else:
                        phantom_moves_vals_list += move._generate_move_phantom(bom_line, line_data['qty'], 0)

            else:
                if move.picking_id.immediate_transfer:
                    factor = move.product_uom._compute_quantity(move.quantity_done, bom.product_uom_id) / bom.product_qty
                else:
                    factor = move.product_uom._compute_quantity(move.product_uom_qty, bom.product_uom_id) / bom.product_qty
                boms, lines = bom.sudo().explode(move.product_id, factor, picking_type=bom.picking_type_id, bom_ids=bom_ids)
                for bom_line, line_data in lines:
                    if move.picking_id.immediate_transfer:
                        phantom_moves_vals_list += move._generate_move_phantom(bom_line, 0, line_data['qty'])
                    else:
                        phantom_moves_vals_list += move._generate_move_phantom(bom_line, line_data['qty'], 0)

            # delete the move with original product which is not relevant anymore
            moves_ids_to_unlink.add(move.id)
        self.env['stock.move'].browse(moves_ids_to_unlink).sudo().unlink()
        if phantom_moves_vals_list:
            phantom_moves = self.env['stock.move'].create(phantom_moves_vals_list)
            phantom_moves._adjust_procure_method()
            moves_ids_to_return |= phantom_moves.action_explode(bom_ids=bom_ids).ids
        return self.env['stock.move'].browse(moves_ids_to_return)