"""

Usage:
    scripts/generate_declaration_export_for_ccs_sourcing.py <data_api_url> <data_api_token> <path_to_manifest>

Example:
    ./generate_declaration_export_for_ccs_sourcing.py http://api myToken /my/path/to/file/manifest.yml
"""
import csv
import sys
import yaml

from docopt import docopt
from dmutils.apiclient import DataAPIClient, HTTPError


def get_or_else_none(map_to_check, key):
    """
        Use map.get to handle missing keys for object values
    """
    return map_to_check.get(key, None)


def get_or_else_empty_string(map_to_check, key):
    """
        Use map.get to handle missing keys for string values
    """
    return map_to_check.get(key, "")


def get_or_else_empty_list(map_to_check, key):
    """
        Use map.get to handle missing keys for list values
    """
    return map_to_check.get(key, [])


def bool_to_yes_no(value):
        """
        Turn a boolean into a yes/no string
        :param value eg True:
        :return string eg "yes":
        """
        if value:
            return "yes"
        return "no"


def has_checked_all_boxes(array, total):
    """
    Return a string indicating length of array compared with expected total

    :param array eg ["value"]:
    :param total eg 2:
    :return "failed":
    """
    if len(array) < total:
        return "failed"
    else:
        return "passed"


def process_boolean(declaration, field):
    value = get_or_else_none(declaration, field)
    if value is not None:
        return bool_to_yes_no(value)
    else:
        return ""


def process_string(declaration, field):
    return get_or_else_empty_string(declaration, field)


def process_checkbox_counts(declaration, field):
    values = get_or_else_empty_list(declaration, field)
    return has_checked_all_boxes(values, expected_totals[field])


def process_list_to_string(declaration, field):
    return ", ".join(get_or_else_empty_list(declaration, field))


# expected length of checkbox groups - if users don't tick all they fail
expected_totals = {
    "SQ1-3": 5,
    "SQC3": 10
}


# map fields to processing method
question_mapping = {
    "PR1": process_boolean,
    "PR2": process_boolean,
    "SQC2": process_boolean,
    "PR5": process_boolean,
    "PR3": process_boolean,
    "PR4": process_boolean,
    "SQ1-3": process_checkbox_counts,
    "SQA2": process_boolean,
    "SQA3": process_boolean,
    "SQA4": process_boolean,
    "SQA5": process_boolean,
    "AQA5": process_boolean,
    "AQA3": process_boolean,
    "SQ5-1a": process_string,
    "SQC3": process_checkbox_counts,
    "SQ1-2a": process_string,
    "SQ1-2b": process_string,
    "SQ1-1a": process_string,
    "SQ1-1b": process_string,
    "SQ1-1ci": process_string,
    "SQ1-1cii": process_string,
    "SQ1-1k": process_string,
    "SQ1-1d-i": process_string,
    "SQ1-1d-ii": process_string,
    "SQ1-1e": process_string,
    "SQ1-1h": process_string,
    "SQ5-2a": process_boolean,
    "SQ1-1i-i": process_boolean,
    "SQ1-1i-ii": process_string,
    "SQ1-1j-i": process_list_to_string,
    "SQ1-1j-ii": process_string,
    "SQ1-1m": process_string,
    "SQE2a": process_list_to_string,
    "SQ1-1n": process_string,
    "SQ1-1o": process_string,
    "SQ2-1abcd": process_boolean,
    "SQ2-1e": process_boolean,
    "SQ2-1f": process_boolean,
    "SQ2-1ghijklmn": process_boolean,
    "SQ2-2a": process_boolean,
    "SQ3-1a": process_boolean,
    "SQ3-1b": process_boolean,
    "SQ3-1c": process_boolean,
    "SQ3-1d": process_boolean,
    "SQ3-1e": process_boolean,
    "SQ3-1f": process_boolean,
    "SQ3-1g": process_boolean,
    "SQ3-1h-i": process_boolean,
    "SQ3-1h-ii": process_boolean,
    "SQ3-1i-i": process_boolean,
    "SQ3-1i-ii": process_boolean,
    "SQ3-1j": process_boolean,
    "SQ3-1k": process_string,
    "SQ4-1a": process_boolean,
    "SQ4-1b": process_boolean,
    "SQ4-1c": process_string,
}


def process_supplier_declaration(supplier_declaration, questions):
    """
    Run through the answers from the supplier and process into a readable format
    - processing methods defined above
    :param supplier_declaration:
    :param questions:
    :return:
    """
    answers = []
    for question in questions:
        if question in question_mapping:
            answers.append(question_mapping[question](supplier_declaration, question))
    return answers


# get the list of questions, in order, from the manifest
def process_declaration_manifest(path_to_manifest):
    """
    Reads the manifest to get the order list of questions
    - Used to ensure that we can match the JSON key (SQ3-1d)
        to the position on the supplier web page (43)
    - this allows for the CSV row to match the order of questions in the manifest
        and subsequently the order on the application
    :param path_to_manifest:
    :return:
    """
    all_the_questions_in_order = []
    with open(path_to_manifest, 'r') as f:
        declaration_pages = yaml.load(f)
        for declaration_page in declaration_pages:
            for question in declaration_page['questions']:
                all_the_questions_in_order.append(question)
    return all_the_questions_in_order


def headers(questions):
    """
    Generate the headers for the CSV file
    - take an array of questions. The order is important
    - Each question id is a column header
    - Paired with the index+1 of it's position in the array
    - Example: 43:SQ3-1d
    - SQ3-1d is the old question id
    - 43 is it's number on the supplier application
    - Note array is prefixed with the DM supplier ID
    :param questions:
    :return array of strings representing headers:
    """
    csv_headers = list()
    csv_headers.append('Digital Marketplace ID')
    csv_headers.append('Digital Marketplace Name')
    csv_headers.append('Digital Marketplace Duns number')
    csv_headers.append('State of Declaration')
    for index, value in enumerate(questions):
        csv_headers.append("{}:{}".format(index+1, value))
    return csv_headers


def suppliers_on_framework(data_api_url, data_api_token, questions):
    """
    Generate the CSV
    - takes the data api details
    - iterates through all suppliers
    - foreach supplier hits the declaration API to recover the answers
    - builds CSV row for each supplier
    :param data_api_url:
    :param data_api_token:
    :param questions:
    :return:
    """
    client = DataAPIClient(data_api_url, data_api_token)

    writer = csv.writer(sys.stdout, delimiter=',', quotechar='"')
    writer.writerow(headers(questions))

    for supplier in client.find_suppliers_iter():
        try:
            selection = client.get_selection_answers(supplier['id'], 'g-cloud-7')
            status = selection['selectionAnswers']['questionAnswers']['status']

            processed_supplier_declaration = \
                process_supplier_declaration(
                    selection['selectionAnswers']['questionAnswers'],
                    questions
                )

            supplier_declaration = list()
            supplier_declaration.append(supplier['id'])
            supplier_declaration.append(supplier['name'])
            supplier_declaration.append(supplier.get('dunsNumber', ""))
            supplier_declaration.append(status)
            for declaration in processed_supplier_declaration:
                supplier_declaration.append(declaration)

            try:
                writer.writerow(supplier_declaration)
            except UnicodeEncodeError:
                writer.writerow(
                    [field.encode('utf-8') if hasattr(field, 'encode') else field for field in supplier_declaration]
                )

        except HTTPError as e:
            if e.status_code == 404:
                # not all suppliers make a declaration so this is fine
                # status = 'unstarted'
                pass
            else:
                # status = 'error-{}'.format(e.status_code)
                raise e
        except KeyError:
            # status = 'error-key-error'
            pass

if __name__ == '__main__':
    arguments = docopt(__doc__)

    suppliers_on_framework(
        data_api_url=arguments['<data_api_url>'],
        data_api_token=arguments['<data_api_token>'],
        questions=process_declaration_manifest(arguments['<path_to_manifest>'])
    )
