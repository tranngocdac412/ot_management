from odoo import models, fields, api
import datetime, holidays

SECONDS_PER_HOUR = 3600

STATES_DICT = {'draft': 'Draft',
               'to_approve': 'To Approve',
               'approved': 'PM Approved',
               'done': 'DL Approved',
               'refused': 'Refused'}

CATEGORY_DICT = {'normal_day': 'Ngày bình thường',                      #18h30-22h
                 'normal_day_morning': 'OT ban ngày (6h-8h30)',         #6h-8h30
                 'normal_day_night': 'Ngày bình thường - Ban đêm',      #6h-8h30
                 'saturday': 'Thứ 7',                                   #6h-22h
                 'sunday': 'Chủ nhật',                                  #6h-22h
                 'weekend_day_night': 'Ngày cuối tuần - Ban đêm',       #
                 'holiday': 'Ngày lễ',                                  #
                 'holiday_day_night': 'Ngày lễ - Ban đêm',              #
                 'compensatory_normal': 'Bù ngày lễ vào ngày thường',   #
                 'compensatory_night': 'Bù ngày lễ vào ban đêm',        #
                 'unknown': 'Không thể xác định'}

class OTRegistration(models.Model):
    _name = 'ot.registration'
    _description = 'OT Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    @api.depends('ot_registration_lines')
    def _compute_total_ot(self):
        for record in self:
            for item in record.ot_registration_lines:
                if item.additional_hours:
                    record.additional_hours += item.additional_hours

    project_id = fields.Many2one('project.project',string='Project')
    manager_id = fields.Many2one('hr.employee', string='Approver')
    ot_month = fields.Date(string='OT Month', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    dl_id = fields.Many2one('hr.employee', string='Department lead', readonly=True)
    additional_hours = fields.Float(string='Total OT', readonly=True, compute='_compute_total_ot', store=True)
    state = fields.Selection([(key, value) for key, value in STATES_DICT.items()],
                             string='State', default='draft', readonly=True)
    ot_registration_lines = fields.One2many('ot.registration.line', 'ot_registration_id', string='OT Registration Lines')


class OTRegistrationLine(models.Model):
    _name = 'ot.registration.line'
    _description = 'OT Registration Line'

    @api.depends('date_from', 'date_to')
    def _compute_category(self):
        vi_holidays = holidays.VN()
        for record in self:
            if record.date_from in vi_holidays or record.date_to in vi_holidays:
                record.category = 'holiday'

    @api.depends('date_from', 'date_to')
    def _compute_ot_hours(self):
        for record in self:
            ot_seconds = (record.date_to - record.date_from).total_seconds()
            record.additional_hours = ot_seconds/SECONDS_PER_HOUR if ot_seconds > 0 else 0

    ot_registration_id = fields.Many2one('ot.registration', string='OT Registration ID')
    employee_id = fields.Many2one('hr.employee', related='ot_registration_id.employee_id')
    project_id = fields.Many2one('project.project', related='ot_registration_id.project_id')
    date_from = fields.Datetime(string='From', default=fields.datetime.now(), required=True)
    date_to = fields.Datetime(string='To', default=fields.datetime.now(), required=True)
    category = fields.Selection([(key, value) for key, value in CATEGORY_DICT.items()], string='OT Category',
                                compute='_compute_category')
    is_wfh = fields.Boolean(string='WFH')
    is_intern = fields.Boolean(string='Is intern', default=False)
    additional_hours = fields.Float(string='Total OT', readonly=True, store=True, compute='_compute_ot_hours')
    job_taken = fields.Char(string='Job Taken')
    is_late_approved = fields.Boolean(string='Late Approved', readonly=True)
    hr_notes = fields.Text(string='HR Notes', readonly=True)
    attendance_notes = fields.Text(string='Attendance Notes')
    notes = fields.Char(string='Warning')
    state = fields.Selection([('draft', 'Draft'),
                              ('to_approve', 'To Approve'),
                              ('approved', 'PM Approved'),
                              ('done', 'DL Approved'),
                              ('refused', 'Refused')],
                             string='State', default='draft', readonly=True)
