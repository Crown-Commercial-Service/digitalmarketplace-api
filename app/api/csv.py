import re
import six
import csvx
from io import StringIO
from collections import OrderedDict as od


def generate_brief_responses_csv(brief, responses):
    def csv_cell_sanitize(text):
        return re.sub(r"^(=|\+|-|@|!|\|{|}|\[|\]|<|,)+", '', unicode(text).strip())

    # converts a brief response into an ordered dict
    def row(r):
        answers = od()

        ess_req_names = brief.data.get('essentialRequirements', [])
        nth_req_names = brief.data.get('niceToHaveRequirements', [])
        ess_responses = r.data.get('essentialRequirements', [''] * len(ess_req_names))
        nth_responses = [r.data.get('niceToHaveRequirements')[i] if
                         i < len(r.data.get('niceToHaveRequirements', [])) else
                         '' for i in range(len(nth_req_names))]

        answers.update({'Supplier': r.supplier.name})
        answers.update({'Email': r.data.get('respondToEmailAddress', 'UNKNOWN')})
        if brief.lot.slug == 'digital-professionals':
            answers.update({'Specialist Name': r.data.get('specialistName', 'UNKNOWN')})

        answers.update({'Availability Date': r.data.get('availability', 'UNKNOWN')})

        if brief.lot.slug == 'training':
            answers.update({'Phone number': r.data.get('contactNumber', '')})
        else:
            answers.update({'Day rate': r.data.get('dayRate', '')})
        answers.update(zip(ess_req_names, ess_responses))
        answers.update(zip(nth_req_names, nth_responses))

        for k, v in answers.items():
            answers[k] = csv_cell_sanitize(v)

        return answers

    # convert the responses to a list - each row is a dict representing a brief response
    rows = [row(_) for _ in responses]
    # add the keys of a dict as the first element in the rows list, to be used as headers
    first = rows[0].keys() if responses else []
    rows = [first] + [_.values() for _ in rows]
    # convert the rows to a zip'd list - this creates a structure so the csv's first column is the headers and the
    # remaining columns contain the data for each header row
    transposed = list(six.moves.zip_longest(*rows))
    csvdata = StringIO()
    with csvx.Writer(csvdata) as csv_out:
        csv_out.write_rows(transposed)
        return csvdata.getvalue()
