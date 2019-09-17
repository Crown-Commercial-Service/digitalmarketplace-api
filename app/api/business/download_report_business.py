import pendulum
from app.api.services import (
    briefs,
    suppliers
)
from app.api.csv import (
    generate_seller_catalogue_csv,
    generate_seller_responses_csv,
    generate_specialist_opportunities_csv,
    generate_atm_opportunities_csv,
    generate_rfx_opportunities_csv,
    generate_training_opportunities_csv
)


def get_result(current_user, report_type, start_date, end_date):
    csv_generator = None
    result = None
    report_file_name = None

    if report_type == 'sellersCatalogue':
        result = suppliers.get_approved_suppliers()
        csv_generator = generate_seller_catalogue_csv
        report_file_name = 'current-approved-seller-catalogue.csv'

    elif report_type == 'sellerResponses':
        result = briefs.get_all_user_seller_responses_within_date_range(
            current_user.id, start_date, end_date
        )
        csv_generator = generate_seller_responses_csv
        report_file_name = "seller_responses_within_" + start_date + "_and_" + end_date + ".csv"

    elif report_type == 'specialist':
        result = briefs.get_oppportunities_for_download(
            current_user.id,
            start_date,
            end_date,
            [
                'specialist'
            ]
        )
        csv_generator = generate_specialist_opportunities_csv
        report_file_name = "specialist_opportunities_within_" + start_date + "_and_" + end_date + ".csv"

    elif report_type == 'atm':
        result = briefs.get_oppportunities_for_download(current_user.id, start_date, end_date, ['atm'])
        csv_generator = generate_atm_opportunities_csv
        report_file_name = "atm_opportunities_within_" + start_date + "_and_" + end_date + ".csv"

    elif report_type == 'rfx':
        result = briefs.get_oppportunities_for_download(
            current_user.id,
            start_date,
            end_date,
            [
                'rfx'
            ]
        )
        csv_generator = generate_rfx_opportunities_csv
        report_file_name = "rfx_opportunities_within_" + start_date + "_and_" + end_date + ".csv"

    elif report_type == 'training':
        result = briefs.get_oppportunities_for_download(current_user.id, start_date, end_date, ['training2'])
        csv_generator = generate_training_opportunities_csv
        report_file_name = "training_opportunities_within_" + start_date + "_and_" + end_date + ".csv"

    return report_file_name, result, csv_generator
