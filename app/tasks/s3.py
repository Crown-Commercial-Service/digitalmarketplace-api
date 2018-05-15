from __future__ import \
    unicode_literals, \
    absolute_import

from . import celery
from flask import current_app
from io import BytesIO
from os import getenv
from app.api.services import brief_responses_service
from app.models import BriefResponse
from werkzeug.utils import secure_filename
import boto3
import botocore
import zipfile


class CreateResumesZipException(Exception):
    """Raised when the resume zip fails to create."""


@celery.task
def create_resumes_zip(brief_id):
    BUCKET_NAME = getenv('S3_BUCKET_NAME')
    s3 = boto3.resource(
        's3',
        region_name=getenv('AWS_REGION'),
        aws_access_key_id=getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=getenv('AWS_SECRET_ACCESS_KEY')
    )
    bucket = s3.Bucket(BUCKET_NAME)

    files = []
    attachments = brief_responses_service.get_all_attachments(brief_id)
    for attachment in attachments:
        files.append({
            'key': 'supplier-{}/{}'.format(attachment['supplier_code'], attachment['file_name']),
            'zip_name': 'brief-{}/{}/{}'.format(
                brief_id,
                secure_filename(attachment['supplier_name']),
                attachment['file_name']
            )
        })

    if not files:
        raise CreateResumesZipException('The brief id "{}" did not have any attachments'.format(brief_id))

    with BytesIO() as archive:
        with zipfile.ZipFile(archive, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                with BytesIO() as s3io:
                    try:
                        bucket.download_fileobj(
                            'digital-marketplace/documents/brief-{}/{}'.format(brief_id, file['key']),
                            s3io
                        )
                        zf.writestr(file['zip_name'], s3io.getvalue())
                    except botocore.exceptions.ClientError as e:
                        raise CreateResumesZipException('The file "{}" failed to download'.format(file))

        archive.seek(0)
        try:
            bucket.upload_fileobj(
                archive,
                'digital-marketplace/archives/brief-{}/brief-{}-resumes.zip'.format(brief_id, brief_id)
            )
        except botocore.exceptions.ClientError as e:
            raise CreateResumesZipException('The resumes archive for brief id "{}" failed to upload'.format(brief_id))
