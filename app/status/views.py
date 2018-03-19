from flask import request
from sqlalchemy.exc import SQLAlchemyError

from . import status
from . import utils
from ..models import Framework
from dmutils.status import get_app_status, StatusError
from app import search_api_client


def get_db_status():
    try:
        return {
            'frameworks': {f.slug: f.status for f in Framework.query.all()},
            'db_version': utils.get_db_version(),
        }

    except SQLAlchemyError:
        raise StatusError('Error connecting to database')


@status.route('/_status')
def status():
    return get_app_status(data_api_client=None,
                          search_api_client=search_api_client,
                          ignore_dependencies='ignore-dependencies' in request.args,
                          additional_checks=[get_db_status])
