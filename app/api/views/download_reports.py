from flask import Response, jsonify, request
from flask_login import login_required, current_user

from app.api import api
from app.api.business.download_report_business import get_result
from app.api.helpers import (exception_logger, permissions_required,
                             role_required)

from ...utils import get_json_from_request


@api.route('/buyer/download/reports', methods=['GET'])
@exception_logger
@login_required
@role_required('buyer')
@permissions_required('download_reports')
def download_reports():
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    report_type = request.args.get('reportType', None)
    output_format = request.args.get('outputFormat', 'csv')
    csv_generator = None
    result = None
    report_file_name = None

    report_file_name, result, csv_generator = get_result(current_user, report_type, start_date, end_date)

    if output_format == 'json':
        return jsonify(result), 200
    else:
        csv_data = csv_generator(result)
        response = Response(csv_data, mimetype='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=' + report_file_name
        return response
