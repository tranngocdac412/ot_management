import datetime
import holidays

import pytz
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

SECONDS_PER_HOUR = 3600

STATES_DICT = {'draft': 'Draft',
               'to_approve': 'To Approve',
               'approved': 'PM Approved',
               'done': 'DL Approved',
               'refused': 'Refused'}

CATEGORY_DICT = {'normal_day': 'Ngày bình thường',
                 'normal_day_morning': 'OT ban ngày (6h-8h30)',
                 'normal_day_night': 'Ngày bình thường - Ban đêm',
                 'saturday': 'Thứ 7',
                 'sunday': 'Chủ nhật',
                 'weekend_day_night': 'Ngày cuối tuần - Ban đêm',
                 'holiday': 'Ngày lễ',
                 'holiday_day_night': 'Ngày lễ - Ban đêm',
                 'compensatory_normal': 'Bù ngày lễ vào ngày thường',
                 'compensatory_night': 'Bù ngày lễ vào ban đêm',
                 'unknown': 'Không thể xác định'}
# CATEGORY = [('normal_day', 'Ngày bình thường'),
#                  ('normal_day_morning', 'OT ban ngày (6h-8h30)'),
#                  ('normal_day_night', 'Ngày bình thường - Ban đêm'),
#                  ('saturday', 'Thứ 7'),
#                  ('sunday', 'Chủ nhật'),
#                  ('weekend_day_night', 'Ngày cuối tuần - Ban đêm'),
#                  ('holiday', 'Ngày lễ'),
#                  ('holiday_day_night', 'Ngày lễ - Ban đêm'),
#                  ('compensatory_normal', 'Bù ngày lễ vào ngày thường'),
#                  ('compensatory_night', 'Bù ngày lễ vào ban đêm'),
#                  ('unknown', 'Không thể xác định')]

class OTRegistration(models.Model):
    _name = 'ot.registration'
    _rec_name = 'employee_id'
    _description = 'OT Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def update_state(self, state):
        for record in self:
            record.state = state
        for record in self.env['ot.registration.line'].sudo().search([('ot_registration_id', '=', self.id)]):
            record.state = state

    def action_submit(self):
        self.update_state('to_approve')

    def button_pm_approve(self):
        self.update_state('approved')

    def button_dl_approve(self):
        self.update_state('done')

    def refuse_request(self):
        self.update_state('refused')

    def draft_request(self):
        self.update_state('draft')

    @api.depends('ot_registration_lines')
    def _compute_total_ot(self):
        for record in self:
            for item in record.ot_registration_lines:
                if item.additional_hours:
                    record.additional_hours += item.additional_hours

    def get_user(self):
        return self.env['hr.employee'].sudo().search([('user_id', '=', self._uid)], limit=1)

    project_id = fields.Many2one('project.project', string='Project')
    manager_id = fields.Many2one('hr.employee', string='Approver')
    ot_month = fields.Date(string='OT Month', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True, default=lambda self: self.get_user())
    company_id = fields.Many2one('res.company', string='Company')
    dl_id = fields.Many2one('hr.employee', string='Department lead', readonly=True, default=2)
    additional_hours = fields.Float(string='Total OT', readonly=True, compute='_compute_total_ot', store=True)
    state = fields.Selection([(key, value) for key, value in STATES_DICT.items()],
                             string='State', default='draft', readonly=True)
    ot_registration_lines = fields.One2many('ot.registration.line', 'ot_registration_id',
                                            string='OT Registration Lines')


class OTRegistrationLine(models.Model):
    _name = 'ot.registration.line'
    _description = 'OT Registration Line'

    @api.constrains('category')
    def _check_category(self):
        for record in self:
            if record.category == 'unknown':
                raise ValidationError(_('Category khong hop le'))
    def compute_is_late_approved(self):
        pass
    def time_type(self, date_from, date_to):
        if datetime.datetime(date_from.year, date_from.month, date_from.day, 6, 0, 0, 0) \
                <= date_from \
                < date_to \
                <= datetime.datetime(date_from.year, date_from.month, date_from.day, 8, 30, 0, 0):
            return 'morning'
        if datetime.datetime(date_from.year, date_from.month, date_from.day, 18, 30, 0, 0) \
                <= date_from \
                < date_to \
                <= datetime.datetime(date_from.year, date_from.month, date_from.day, 22, 00, 0, 0):
            return 'normal'
        if datetime.datetime(date_from.year, date_from.month, date_from.day, 6, 0, 0, 0) \
                <= date_from \
                < date_to \
                <= datetime.datetime(date_from.year, date_from.month, date_from.day, 22, 00, 0, 0):
            return 'day'
        if datetime.datetime(date_from.year, date_from.month, date_from.day, 22, 0, 0, 0) \
                <= date_from \
                < date_to \
                <= datetime.datetime(date_from.year, date_from.month, date_from.day + 1, 6, 00, 0, 0):
            return 'night'
        return 'unknown'
    def date_type(self, date_from, date_to):
        vi_holidays = holidays.VN()
        if date_from in vi_holidays or date_to in vi_holidays:
            return 'holiday'
        if date_from.weekday() == 5:
            return 'saturday'
        if date_from.weekday() == 6:
            return 'sunday'
        return 'unknown'

    @api.depends('date_from', 'date_to')
    def _compute_category(self):
        for record in self:
            date_type = self.date_type(self.tz_utc_to_local(record.date_from), self.tz_utc_to_local(record.date_to))
            time_type = self.time_type(self.tz_utc_to_local(record.date_from), self.tz_utc_to_local(record.date_to))
            if date_type == 'holiday':
                if time_type == 'morning' or 'normal' or 'day':
                    record.category = 'holiday'
                elif time_type == 'night':
                    record.category = 'holiday_day_night'
                else:
                    record.category = 'unknown'
            elif date_type == 'saturday':
                if time_type == 'morning' or 'normal' 'day':
                    record.category = 'saturday'
                elif time_type == 'night':
                    record.category = 'weekend_day_night'
                else:
                    record.category = 'unknown'
            elif date_type == 'sunday':
                if time_type == 'morning' or 'normal' or 'day':
                    record.category = 'sunday'
                elif time_type == 'night':
                    record.category = 'weekend_day_night'
                else:
                    record.category = 'unknown'
            else:
                if time_type == 'morning':
                    record.category = 'normal_day_morning'
                elif time_type == 'normal':
                    record.category = 'normal_day'
                elif time_type == 'night':
                    record.category = 'normal_day_night'
                else:
                    record.category = 'unknown'
    @api.depends('date_from', 'date_to', 'category')
    def _compute_ot_hours(self):
        for record in self:
            ot_seconds = (record.date_to - record.date_from).total_seconds()
            record.additional_hours = ot_seconds / SECONDS_PER_HOUR if record.category != 'unknown' else 0

    def tz_utc_to_local(self, utc_time):
        return utc_time + self.utc_offset()

    def utc_offset(self):
        user_timezone = self.env.user.tz or 'GMT'
        hours = int(datetime.datetime.now(pytz.timezone(user_timezone)).strftime('%z')[:3])
        return datetime.timedelta(hours=hours)

    ot_registration_id = fields.Many2one('ot.registration', string='OT Registration ID', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='ot_registration_id.employee_id', store=True)
    project_id = fields.Many2one('project.project', related='ot_registration_id.project_id', store=True)
    date_from = fields.Datetime(string='From', default=fields.datetime.now(), required=True)
    date_to = fields.Datetime(string='To', default=fields.datetime.now(), required=True)
    category = fields.Selection([(key, value) for key, value in CATEGORY_DICT.items()], string='OT Category',
                                compute='_compute_category', store=True)
    is_wfh = fields.Boolean(string='WFH')
    is_intern = fields.Boolean(string='Is intern', default=False)
    additional_hours = fields.Float(string='Total OT', readonly=True, compute='_compute_ot_hours', store=True)
    job_taken = fields.Char(string='Job Taken', default='N/A')
    is_late_approved = fields.Boolean(string='Late Approved', readonly=True, compute='compute_is_late_approved', store=True)
    hr_notes = fields.Text(string='HR Notes', readonly=True)
    attendance_notes = fields.Text(string='Attendance Notes', readonly=True)
    notes = fields.Char(string='Warning', default='Exceed OT plan', readonly=True)
    state = fields.Selection([(key, value) for key, value in STATES_DICT.items()],
                             string='State', default='draft', readonly=True, store=True)
