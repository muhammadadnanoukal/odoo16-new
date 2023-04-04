from odoo import api, fields, models, _, Command

class CrmLead(models.Model):
    """ Manufacturing Orders """
    _inherit = 'crm.lead'
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', index=True, tracking=True,
        compute='_compute_stage_id', readonly=True, store=True,
        copy=False, group_expand='_read_group_stage_ids', ondelete='restrict',
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]")
    quotation_ids = fields.One2many('sale.order', 'opportunity_id', string='Opportunity')
    quotation_count = fields.Integer(compute='_compute_quotation_count')
    check_status = fields.Selection([('compatible', 'Compatible'), ('not_compatible', 'Not Compatible')],
                                    string='Stage Status', default='compatible', readonly=True)

    @api.onchange('quotation_ids')
    def _compute_quotation_count(self):
        first_stage = self.env['crm.stage'].search(['|', ('name', '=', 'New'), ('state', '=', '')])

        for rec in self:
            rec.quotation_count = len(self.quotation_ids)
            if rec.quotation_count == 0:
                if first_stage:
                    rec.check_status = 'compatible'
                    rec.stage_id = first_stage.id
