from __future__ import absolute_import, unicode_literals

import zipfile
from io import BytesIO
from os import getenv

import boto3
import botocore
from flask import current_app, render_template
from jinja2 import Environment, PackageLoader, select_autoescape
from werkzeug.utils import secure_filename

from app import db
from app.api.csv import generate_brief_responses_csv
from app.api.services import brief_responses_service
from app.models import Brief, BriefResponse
from app.api.helpers import prepare_specialist_responses

from . import celery


class CreateResponsesZipException(Exception):
    """Raised when the resume zip fails to create."""


template_env = Environment(
    loader=PackageLoader('app.tasks', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


@celery.task
def create_responses_zip(brief_id):
    brief = Brief.query.filter(Brief.id == brief_id).first_or_404()
    responses = BriefResponse.query.filter(
        BriefResponse.brief_id == brief_id,
        BriefResponse.withdrawn_at.is_(None)
    ).all()

    if not brief:
        raise CreateResponsesZipException('Failed to load brief for id {}'.format(brief_id))

    if not responses:
        raise CreateResponsesZipException('There were no respones for brief id {}'.format(brief_id))

    if brief.lot.slug not in ['digital-professionals', 'training', 'rfx', 'atm']:
        raise CreateResponsesZipException('Brief id {} is not a compatible lot'.format(brief_id))

    BUCKET_NAME = getenv('S3_BUCKET_NAME')
    s3 = boto3.resource(
        's3',
        region_name=getenv('AWS_REGION'),
        aws_access_key_id=getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=getenv('AWS_SECRET_ACCESS_KEY'),
        endpoint_url=getenv('AWS_S3_URL')
    )
    bucket = s3.Bucket(BUCKET_NAME)

    files = []
    attachments = brief_responses_service.get_all_attachments(brief_id)
    for attachment in attachments:
        if attachment['file_name'].startswith('digital-marketplace') and '/' in attachment['file_name']:
            key = attachment['file_name']
            zip_file_name = attachment['file_name'].split('/')[-1]
        else:
            key = 'digital-marketplace/documents/brief-{}/supplier-{}/{}'.format(brief_id,
                                                                                 attachment['supplier_code'],
                                                                                 attachment['file_name'])
            zip_file_name = attachment['file_name']
        files.append({
            'key': key,
            'zip_name': 'opportunity-{}-documents/{}/{}'.format(
                brief_id,
                secure_filename(attachment['supplier_name']),
                zip_file_name
            )
        })

    with BytesIO() as archive:
        with zipfile.ZipFile(archive, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                s3file = file['key']
                with BytesIO() as s3io:
                    try:
                        bucket.download_fileobj(s3file, s3io)
                        zf.writestr(file['zip_name'], s3io.getvalue())
                    except botocore.exceptions.ClientError as e:
                        raise CreateResponsesZipException('The file "{}" failed to download'.format(s3file))

            csvdata = generate_brief_responses_csv(brief, responses)
            csv_file_name = ('opportunity-{}-raw.csv'.format(brief_id)
                             if brief.lot.slug == 'digital-professionals'
                             else 'responses-to-requirements-{}.csv'.format(brief_id))
            zf.writestr(csv_file_name, csvdata.encode('utf-8'))

            if brief.lot.slug == 'digital-professionals':
                sorted_responses = sorted(
                    responses,
                    key=lambda response: (response.supplier.name, response.data.get('specialistName', 'Unknown'))
                )

                compliance_check_template = template_env.get_template('compliance-check.html')
                compliance_check_html = render_template(
                    compliance_check_template,
                    brief=brief,
                    responses=sorted_responses
                )
                zf.writestr('compliance-check-{}.html'.format(brief_id), compliance_check_html.encode('utf-8'))

                candidates = prepare_specialist_responses(brief, sorted_responses)

                response_criteria_template = template_env.get_template('response-criteria.html')
                response_criteria_html = render_template(
                    response_criteria_template,
                    brief=brief,
                    candidates=candidates
                )
                zf.writestr('responses-{}.html'.format(brief_id), response_criteria_html.encode('utf-8'))

        archive.seek(0)

        try:
            brief.responses_zip_filesize = len(archive.getvalue())
            db.session.add(brief)
            db.session.commit()
        except Exception as e:
            raise CreateResponsesZipException(str(e))

        try:
            bucket.upload_fileobj(
                archive,
                'digital-marketplace/archives/brief-{}/brief-{}-resumes.zip'.format(brief_id, brief_id)
            )
        except botocore.exceptions.ClientError as e:
            raise CreateResponsesZipException('The responses archive for brief id "{}" failed to upload'
                                              .format(brief_id))
