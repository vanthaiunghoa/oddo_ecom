from odoo import models, fields, api, _


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    patient_name = fields.Char(string='Patient Name')


class HospitalPatient(models.Model):
    _name = 'hospital.patient'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'name_sec'
    _description = 'Patient Record'

    patient_name = fields.Char(string='Name', required=True)
    patient_age = fields.Integer('Age')
    notes = fields.Text(string='Notes')
    image = fields.Binary(string='Image')
    name = fields.Text(string='Text')
    name_sec = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                           index=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name_sec', _('New')) == _('New'):
            vals['name_sec'] = self.env['ir.sequence'].next_by_code('hospital.patient.sequence') or _('New')

        result = super(HospitalPatient, self).create(vals)
        return result
