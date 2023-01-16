import logging
from odoo.http import request
from odoo import http, _
logger = logging.getLogger(__name__)


class OTController(http.Controller):
    @http.route('/ot_management/<int:id>', type='http', auth='user', website=True)
    def ot_registration_url(self, id):
        menu_id = request.env.ref('ot_management.ot_request').id
        action_id = request.env.ref('ot_management.action_ot_request').id
        link_format = "/web#id={}&view_type=form&model=ot.registration&menu_id={}&action={}"
        link = link_format.format(id, menu_id, action_id)
        return request.redirect(link)
