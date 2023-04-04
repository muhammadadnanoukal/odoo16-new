from odoo import api, fields, models, _
from collections import defaultdict
from odoo.tools import frozendict, lazy_classproperty, ormcache, \
    Collector, LastOrderedSet, OrderedSet
from lxml import etree
import json
import logging
from odoo.addons.stock.models.stock_rule import ProcurementException

from datetime import timedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero, html_escape

from odoo.tools import float_compare, float_round
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"
    customize = fields.Boolean(string='Customize Products')

    # show_update_price_unit = fields.Boolean(default=False, compute='_compute_show_update_price_unit')
    #
    # @api.depends('customize', 'order_line')
    # def _compute_show_update_price_unit(self):
    #     if self.customize and self.order_line and self._origin.order_line != self.order_line:
    #         self.show_update_price_unit = True
    #     else:
    #         self.show_update_price_unit = False

    def update_prices_from_bom(self):
        self.ensure_one()
        lines_to_update = []
        for line in self.order_line:
            lines_to_update.append((1, line.id, {'price_unit': line.mo_bom_id.total_amount}))
        self.update({'order_line': lines_to_update})
        # self.show_update_price_unit = False
        self.message_post(body=_("Product prices have been recomputed according to each bom selected"))

    estimated_installation_date_total = fields.Float(string="Estimated Installation Date", store=True, tracking=4,
                                                     readonly=True, compute='_compute_installation_amounts')

    @api.depends('order_line.total_installation_date_1')
    def _compute_installation_amounts(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.estimated_installation_date_total = sum(order_lines.mapped('total_installation_date_1'))


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        if self._context.get("skip_procurement"):
            return True
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        bom_ids = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                continue
            if line.mo_bom_id:
                qty = line.get_qty_procurement(previous_product_uom_qty)
            else:
                qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            if line.mo_bom_id:
                bom_ids.append(line.mo_bom_id.id)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty
            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements and len(bom_ids) > 0:
            self.env['procurement.group'].run(procurements, bom_ids)
        elif procurements:
            self.env['procurement.group'].run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True

    @api.onchange('price_unit')
    def _onchange_total_amount(self):
        for line in self:
            if line.mo_bom_id:
                line.price_unit = line.mo_bom_id.total_amount

    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver', digits='Product Unit of Measure')
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    customize = fields.Boolean(string='Customize', related="product_template_id.customize")
    mo_bom_id = fields.Many2one('mrp.bom', 'Components')
    total_installation_date_1 = fields.Float('Total Installation Date',
                                             store=True, compute='_compute_estimated_installation_date_total')

    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', related="order_id.pricelist_id", store=True,
                                   readonly=False)
    price_unit = fields.Float('Unit Price', required=True, related="mo_bom_id.total_amount", store=True)
    testing_price = fields.Float("customize price", related="mo_bom_id.total_amount")

    @api.onchange('product_uom_qty', 'mo_bom_id')
    def _compute_estimated_installation_date_total(self):
        for rec in self:
            rec.total_installation_date_1 = rec.mo_bom_id.total_installation_date
            rec.total_installation_date_1 = rec.total_installation_date_1 * rec.product_uom_qty

    @api.onchange('product_template_id', 'mo_bom_id')
    def onchange_product_template_id(self):
        for line in self:
            return {'domain': {'mo_bom_id': ['|', ('product_tmpl_id', '=', line.product_template_id.id), (
                'byproduct_ids.product_id.product_tmpl_id', '=', line.product_template_id.id)]}}

    @api.onchange('mo_bom_id')
    def _onchange_mo_bom_id(self):
        self.mo_bom_id.sequence = 0
        seq_num = 1
        for bom in self.product_template_id.bom_ids:
            if bom.id != self.mo_bom_id.id:
                bom.sequence = seq_num
                seq_num += 1

    @api.depends('product_uom_qty', 'qty_delivered', 'product_id', 'state')
    def _compute_qty_to_deliver(self):
        """The inventory widget should now be visible in more cases if the product is consumable."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if line.state in ('draft', 'sent',
                              'sale') and line.product_type == 'product' and line.product_uom and line.qty_to_deliver > 0:
                if line.state == 'sale' and not line.move_ids:
                    line.display_qty_widget = False
                else:
                    line.display_qty_widget = True
            else:
                line.display_qty_widget = False
        for line in self:
            if line.mo_bom_id:
                # Hide the widget for kits since forecast doesn't support them.
                boms = self.env['mrp.bom']
                if line.state == 'sale':
                    boms = line.move_ids.mapped('bom_line_id.bom_id')
                elif line.state in ['draft', 'sent'] and line.product_id:
                    bom_id = [line.mo_bom_id.id] if line.mo_bom_id else False
                    boms = \
                        boms._bom_find(line.product_id, company_id=line.company_id.id,
                                       bom_type=['phantom', 'assembled'],
                                       bom_ids=bom_id)[
                            line.product_id]
                relevant_bom = boms.filtered(
                    lambda b: (b.type == 'phantom' or b.type == 'assembled' or b.type == 'normalWithPrice') and
                              (b.product_id == line.product_id or
                               (
                                       b.product_tmpl_id == line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    line.display_qty_widget = False
                    continue
                if line.state == 'draft' and line.product_type == 'consu':
                    components = line.product_id.get_components()
                    if components and components != [line.product_id.id]:
                        line.display_qty_widget = True
            else:
                boms = self.env['mrp.bom']
                if line.state == 'sale':
                    boms = line.move_ids.mapped('bom_line_id.bom_id')
                elif line.state in ['draft', 'sent'] and line.product_id:
                    boms = \
                        boms._bom_find(line.product_id, company_id=line.company_id.id,
                                       bom_type=['phantom', 'assembled'])[
                            line.product_id]
                relevant_bom = boms.filtered(lambda b: (b.type == 'phantom' or b.type == 'assembled') and
                                                       (b.product_id == line.product_id or
                                                        (
                                                                b.product_tmpl_id == line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    line.display_qty_widget = False
                    continue
                if line.state == 'draft' and line.product_type == 'consu':
                    components = line.product_id.get_components()
                    if components and components != [line.product_id.id]:
                        line.display_qty_widget = True

    def get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        # Specific case when we change the qty on a SO for a kit product.
        # We don't try to be too smart and keep a simple approach: we compare the quantity before
        # and after update, and return the difference. We don't take into account what was already
        # sent, or any other exceptional case.
        bom = \
            self.env['mrp.bom']._bom_find(self.product_id, bom_type=['phantom', 'assembled'],
                                          bom_ids=[self.mo_bom_id.id])[
                self.product_id]
        if bom:
            return previous_product_uom_qty and previous_product_uom_qty.get(self.id, 0.0) or self.qty_delivered
        return False


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    mrp_production_ids = fields.One2many('mrp.production', 'procurement_group_id')

    @api.model
    def run(self, procurements, bom_ids=False, raise_user_error=True):
        """ If 'run' is called on a kit, this override is made in order to call
        the original 'run' method with the values of the components of that kit.
        """
        procurements_without_kit = []
        product_by_company = defaultdict(OrderedSet)
        for procurement in procurements:
            product_by_company[procurement.company_id].add(procurement.product_id.id)
        kits_by_company = {
            company: self.env['mrp.bom']._bom_find(self.env['product.product'].browse(product_ids),
                                                   company_id=company.id, bom_type=['phantom', 'assembled'],
                                                   bom_ids=bom_ids)
            for company, product_ids in product_by_company.items()
        }
        if not bom_ids:
            for procurement in procurements:
                bom_kits = kits_by_company[procurement.company_id].get(procurement.product_id)
                if bom_kits:
                    order_qty = procurement.product_uom._compute_quantity(procurement.product_qty,
                                                                          bom_kits.product_uom_id, round=False)
                    qty_to_produce = (order_qty / bom_kits.product_qty)
                    boms, bom_sub_lines = bom_kits.explode(procurement.product_id, qty_to_produce)
                    for bom_line, bom_line_data in bom_sub_lines:
                        bom_line_uom = bom_line.product_uom_id
                        quant_uom = bom_line.product_id.uom_id
                        # recreate dict of values since each child has its own bom_line_id
                        values = dict(procurement.values, bom_line_id=bom_line.id)
                        component_qty, procurement_uom = bom_line_uom._adjust_uom_quantities(bom_line_data['qty'],
                                                                                             quant_uom)
                        procurements_without_kit.append(self.env['procurement.group'].Procurement(
                            bom_line.product_id, component_qty, procurement_uom,
                            procurement.location_id, procurement.name,
                            procurement.origin, procurement.company_id, values))
                else:
                    procurements_without_kit.append(procurement)
        else:
            frequent_bom = []
            for procurement in procurements:
                bom_kits = kits_by_company[procurement.company_id].get(procurement.product_id)
                if bom_kits[0]:
                    for bom_kit in bom_kits:
                        if bom_kit in frequent_bom:
                            continue
                        frequent_bom.append(bom_kit)
                        order_qty = procurement.product_uom._compute_quantity(procurement.product_qty,
                                                                              bom_kit.product_uom_id, round=False)
                        qty_to_produce = (order_qty / bom_kit.product_qty)
                        boms, bom_sub_lines = bom_kit.explode(procurement.product_id, qty_to_produce, bom_ids)
                        for bom_line, bom_line_data in bom_sub_lines:
                            bom_line_uom = bom_line.product_uom_id
                            quant_uom = bom_line.product_id.uom_id
                            # recreate dict of values since each child has its own bom_line_id
                            values = dict(procurement.values, bom_line_id=bom_line.id)
                            component_qty, procurement_uom = bom_line_uom._adjust_uom_quantities(bom_line_data['qty'],
                                                                                                 quant_uom)
                            procurements_without_kit.append(self.env['procurement.group'].Procurement(
                                bom_line.product_id, component_qty, procurement_uom,
                                procurement.location_id, procurement.name,
                                procurement.origin, procurement.company_id, values))
                else:
                    procurements_without_kit.append(procurement)
        return super(ProcurementGroup, self).run(procurements_without_kit, raise_user_error=raise_user_error)
