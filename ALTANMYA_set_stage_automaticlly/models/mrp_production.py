from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'mrp.production'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     vals = super(SaleOrder, self).create(vals_list)
    #     for val in vals:
    #         print("val", val)
    #         val_state = None
    #         if val.state == 'draft':
    #             # val_state = val.search([('state', '=', 'draft')])
    #             val_state = val.state
    #         print("val_state", val_state)
    #
    #         if val_state:
    #             print("eeeee")
    #             sale_order_ids = val.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
    #             sale_order_ids = val.env['sale.order'].browse(sale_order_ids)
    #             for sale in sale_order_ids:
    #                 print('sale', sale)
    #                 stage = sale.env['crm.stage'].search(
    #                     [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'draft')],
    #                     order='id desc', limit=1)
    #                 print('stage', stage)
    #                 if stage:
    #                     print('YES')
    #                     if sale.opportunity_id.id:
    #                         print('ALSO YES')
    #                         if sale.opportunity_id.stage_id.id != stage.id:
    #                             print('sale.opportunity_id.stage_id.id != stage.id:')
    #                             print('One')
    #                             print(sale.opportunity_id.stage_id)
    #                             sale.opportunity_id.check_status = 'compatible'
    #                             print(sale.opportunity_id.check_status)
    #                             sale.opportunity_id.stage_id = stage.id
    #                             print('Two')
    #                             print(sale.opportunity_id.stage_id)
    #                 else:
    #                     print("notttttt cooomp")
    #                     sale.opportunity_id.check_status = 'not_compatible'
    #
    #     return vals

    def action_confirm(self):
        super().action_confirm()

        sale_order_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
        sale_order_ids = self.env['sale.order'].browse(sale_order_ids)
        for sale in sale_order_ids:
            stage = sale.env['crm.stage'].search(
                [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'confirmed')], order='id desc',
                limit=1)
            if stage:
                if sale.opportunity_id.id:
                    if sale.opportunity_id.stage_id.id != stage.id:
                        sale.opportunity_id.stage_id = stage.id
                        sale.opportunity_id.check_status = 'compatible'
            else:
                stage = sale.env['crm.stage'].search(
                    [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'approve')], order='id desc',
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

    def action_cancel(self):
        res = super().action_cancel()
        sale_order_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
        sale_order_ids = self.env['sale.order'].browse(sale_order_ids)
        for sale in sale_order_ids:
            stage = sale.env['crm.stage'].search(
                [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'cancel')], order='id desc', limit=1)
            if stage:
                if sale.opportunity_id.id:
                    if sale.opportunity_id.stage_id.id != stage.id:
                        sale.opportunity_id.stage_id = stage.id
                        sale.opportunity_id.check_status = 'compatible'
            else:
                stage_seq = len(self.env['crm.stage'].search([])) - 1
                sale.opportunity_id.check_status = 'not_compatible'
                sale.opportunity_id.stage_id = self.env['crm.stage'].search(
                    [('sequence', '=', stage_seq)], order='id desc', limit=1).id
        return res

    def button_mark_done(self):
        res = super().button_mark_done()
        sale_order_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
        sale_order_ids = self.env['sale.order'].browse(sale_order_ids)

        for sale in sale_order_ids:
            stage = sale.env['crm.stage'].search(
                [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'done')], order='id desc', limit=1)
            if stage:
                if sale.opportunity_id.id:
                    if sale.opportunity_id.stage_id.id != stage.id:
                        sale.opportunity_id.check_status = 'compatible'
            else:
                stage = sale.env['crm.stage'].search(
                    [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'confirmed')], order='id desc',
                    limit=1)
                if stage:
                    if sale.opportunity_id.id:
                        if sale.opportunity_id.stage_id.id != stage.id:
                            sale.opportunity_id.stage_id = stage.id
                            sale.opportunity_id.check_status = 'compatible'
                else:
                    stage = sale.env['crm.stage'].search(
                        [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'approve')], order='id desc',
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
        return res

    def action_approve(self):
        res = super().action_approve()
        sale_order_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids
        sale_order_ids = self.env['sale.order'].browse(sale_order_ids)
        for sale in sale_order_ids:
            stage = sale.env['crm.stage'].search(
                [('state', '=', 'manufacturing'), ('manufacturing_selection', '=', 'approve')], order='id desc',
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

        return res
