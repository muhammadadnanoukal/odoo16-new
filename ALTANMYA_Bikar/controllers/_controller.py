from odoo import http
from odoo.http import request

class CustomCatalogController(http.Controller):

    @http.route('/catalog', type='http', auth="public")
    def download_file(self):
        # file_path = '/ALTANMYA_Bikar/Catalog.pdf'
        record = request.env['documents.document'].search([('name','=','Catalog.pdf')])
        if not record or not record.exists():
            raise request.not_found()

        return request.env['ir.binary']._get_stream_from(record, 'datas').get_response(as_attachment=True)