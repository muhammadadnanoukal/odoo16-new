import logging
from odoo import api, fields, models, _
from collections import defaultdict

from odoo.osv.expression import AND

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bom_id = fields.Many2one(
        'mrp.bom', 'Component', readonly=False,
        domain="""[
        '&',
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
               ('product_tmpl_id','=',product_template_id),
        ('type', '=', 'normal'),
        ('worked', '=', True)]""",
        check_company=True, compute='_compute_bom_id', store=True, precompute=True,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")


    @api.depends('product_id')
    def _compute_bom_id(self):
        for sol in self:
            if not sol.product_id and not sol.bom_id:
                sol.bom_id = False
                continue
            boms_by_product = self.env['mrp.bom'].with_context(active_test=True, just_worked=True)._bom_find(sol.product_id,
                                                                                           company_id=sol.company_id.id,
                                                                                           bom_type='normal')
            if not sol.bom_id or sol.bom_id.product_tmpl_id != sol.product_template_id or (
                    sol.bom_id.product_id and sol.bom_id.product_id != sol.product_id):
                bom = boms_by_product[sol.product_id]
                sol.bom_id = bom.id or False

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        for record in self:
            record.product_id = record.bom_id.product_id

    # def _get_matching_bom(self):
    #     return self.env['mrp.bom']._bom_find(pr, bom_type='normal', company_id=self.company_id.id)[product_id]