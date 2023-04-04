from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        for rec in self:
            mrp_production_id = self.env['mrp.production'].search([
                ('procurement_group_id', '=', rec.group_id.id), ('procurement_group_id', '!=', False)])
            if mrp_production_id:
                sale_order_ids = mrp_production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
                sale_order_ids = mrp_production_id.env['sale.order'].browse(sale_order_ids)
                for sale in sale_order_ids:
                    stage = sale.env['crm.stage'].search(
                        [('state', '=', 'operation_type_manufacturing'),
                         ('operation_type_manufacturing', '=', self.picking_type_id.id)], order='id desc', limit=1)
                    if stage:
                        if mrp_production_id.state == 'done':
                            if sale.opportunity_id.id:
                                if sale.opportunity_id.stage_id.id != stage.id:
                                    sale.opportunity_id.stage_id = stage.id
                                    sale.opportunity_id.check_status = 'compatible'
                    else:
                        stage = sale.env['crm.stage'].search(
                            [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'done')],
                            order='id desc', limit=1)
                        if stage:
                            if sale.opportunity_id.id:
                                if sale.opportunity_id.stage_id.id != stage.id:
                                    sale.opportunity_id.check_status = 'compatible'
                        else:
                            stage = sale.env['crm.stage'].search(
                                [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'confirmed')],
                                order='id desc',
                                limit=1)
                            if stage:
                                if sale.opportunity_id.id:
                                    if sale.opportunity_id.stage_id.id != stage.id:
                                        sale.opportunity_id.stage_id = stage.id
                                        sale.opportunity_id.check_status = 'compatible'
                            else:
                                stage = sale.env['crm.stage'].search(
                                    [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'approve')],
                                    order='id desc',
                                    limit=1)
                                if stage:
                                    if sale.opportunity_id.id:
                                        if sale.opportunity_id.stage_id.id != stage.id:
                                            sale.opportunity_id.stage_id = stage.id
                                            sale.opportunity_id.check_status = 'compatible'
                                else:
                                    check_quotations = self.env['crm.lead'].search(
                                        [('id', '=', sale.opportunity_id)]).quotation_ids.ids
                                    if stage.state == 'sales_status' and stage.sales_status_selection == 'draft':
                                        if len(check_quotations) >= 1:
                                            sale.opportunity_id.check_status = 'compatible'
                                            sale.opportunity_id.write({'stage_id': stage.id})
                                    else:
                                        sale.opportunity_id._compute_quotation_count()
                                        sale.opportunity_id.check_status = 'not_compatible'

            else:
                sale_order_ids = rec.group_id.sale_id.id
                sale_order_ids = rec.env['sale.order'].browse(sale_order_ids)
                for sale in sale_order_ids:
                    stage = sale.env['crm.stage'].search([('state', '=', 'operation_type_sales'),
                                                          ('operation_type_sales', '=', self.picking_type_id.id)],
                                                         order='id desc',
                                                         limit=1)
                    print("stage", stage)
                    if stage:
                        print("trewq")
                        if sale.opportunity_id.id:
                            if sale.opportunity_id.stage_id.id != stage.id:
                                sale.opportunity_id.stage_id = stage.id
                                sale.opportunity_id.check_status = 'compatible'
                    else:
                        stages = self.env['crm.stage'].search([], order='sequence desc')
                        for stage in stages:
                            if stage.state == 'sales_status' and stage.sales_status_selection == 'sale':
                                print("its trigger her111")
                                sale.opportunity_id.check_status = 'compatible'
                                sale.opportunity_id.stage_id = stage.id
                            else:
                                print("111222111222")
                                """get the final approval to here"""
                                "/////////////////////////////////////////////////"
                                print("stage", stage)
                                if stage.state == 'sales_status' and stage.sales_status_selection == 'tentative/final approval':
                                    print("11")
                                    sale.opportunity_id.stage_id = stage.id
                                    sale.opportunity_id.check_status = 'compatible'
                                    print("truuuuuuuuuuuu")
                                else:
                                    check_quotations = self.env['crm.lead'].search(
                                        [(
                                            'id', '=',
                                            sale.opportunity_id)]).quotation_ids.ids
                                    if stage.state == 'sales_status' and stage.sales_status_selection == 'draft':
                                        if len(check_quotations) >= 1:
                                            sale.opportunity_id.check_status = 'compatible'
                                            sale.opportunity_id.write({'stage_id': stage.id})
                                    else:
                                        sale.opportunity_id._compute_quotation_count()
                                        sale.opportunity_id.check_status = 'not_compatible'
                                sale.opportunity_id.check_status = 'not_compatible'
        return res
