from flask import jsonify, abort
from .. import main
from app.api.business.download_report_business import get_admin_report


@main.route('/admin/report/<string:report_type>/download', methods=['GET'])
def download_reports(report_type):
    if report_type is None:
        abort(400, 'report_type is missing')

    report_file_name, csv_data = get_admin_report(report_type)

    return jsonify({
        'data': csv_data,
        'filename': report_file_name
    })
