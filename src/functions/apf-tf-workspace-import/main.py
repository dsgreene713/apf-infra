import os
from pathlib import Path
import tarfile
import boto3
import json
import requests
from requests.exceptions import HTTPError
import logging
from jinja2 import Environment, FileSystemLoader
from exceptions import TFEWorkspaceConfigUploadException

logger = logging.getLogger()
logger.setLevel(logging.INFO)

tfe_base_url = 'https://app.terraform.io/api/v2'


def get_tfe_auth_token():
    client = boto3.client('secretsmanager')
    return client.get_secret_value(SecretId=os.environ['TFE_AUTH_TOKEN_SECRET'])['SecretString']


def get_headers(token=get_tfe_auth_token()) -> dict:
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/vnd.api+json',
    }


def make_tarfile(output: str, source_dir: str, source_files: list):
    # tarfile extraction must be flat so we cd into the source dir first
    # https://developer.hashicorp.com/terraform/enterprise/run/api#2-create-the-file-for-upload
    os.chdir(source_dir)

    with tarfile.open(output, "w:gz") as tar:
        for sfile in source_files:
            tar.add(sfile)


def get_active_accounts():
    client = boto3.client('dynamodb')

    response = client.query(
        ExpressionAttributeValues={':v1': {'S': 'active'}},
        IndexName=os.environ['ACCT_STATUS_GSI'],
        KeyConditionExpression=f'{os.environ['ACCT_STATUS_ATTRIBUTE']} = :v1',
        TableName=os.environ['DYNAMODB_ACCT_TABLE'],
    )

    return response['Items']


def make_requests_call(method: str, endpoint: str, payload=None, data=None):
    if payload is None:
        payload = {}
    if data is None:
        data = {}

    try:
        call = getattr(requests, method)
        url = f'{tfe_base_url}/{endpoint}'
        logger.info(f'calling {url} with:')
        logger.info(f'payload={payload}')
        logger.info(f'data={data}')
        response = call(url, headers=get_headers(), params=payload, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except HTTPError as http_err:
        logger.error(f'HTTP error occurred: {http_err}')
        raise http_err
    except Exception as err:
        logger.error(f'Other error occurred: {err}')
        raise err


def get_template_data():
    return [{
        'acct_id': acct['acct_id']['S'],
        'acct_email': acct['acct_email']['S'],
        'acct_name': acct['acct_name']['S'],
    } for acct in get_active_accounts()]


def render_template(data: list, output_dir: str, tf_file: str):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('accounts_template.j2')
    rendered = template.render({'accounts': data})
    rendered_file = os.path.join(output_dir, tf_file)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with open(rendered_file, 'w') as f:
        f.write(rendered)


def upload_configuration(source_dir: str, upload_file: str, upload_url: str):
    gzip_file = os.path.join(source_dir, upload_file)
    upload = {'file': (gzip_file, open(gzip_file, 'rb'), 'application/octet-stream', {'Expires': '0'})}
    logger.info(f'uploading {upload_file} to {upload_url}')
    response = requests.put(upload_url, files=upload)

    if response.status_code == 200:
        logger.info('successfully uploaded configuration')
        return {'status_code': response.status_code}
    else:
        error = f'failed to upload configuration: status_code={response.status_code}'
        logger.warning(error)
        raise TFEWorkspaceConfigUploadException(error)


def lambda_handler(event, context):
    tfe_workspace = os.environ['TFE_ACCT_IMPORT_WORKSPACE']
    render_dir = os.path.join(os.environ['BASE_OUTPUT_PATH'], 'tf_import')
    rendered_tf_file = 'import.tf'
    config_file = 'import.tar.gz'

    # create the terraform file which will import accounts
    render_template(data=get_template_data(), output_dir=render_dir, tf_file=rendered_tf_file)

    # create a gzipped tar file for the tfe configuration
    make_tarfile(output=config_file, source_dir=render_dir, source_files=[rendered_tf_file])

    # send request to tfe api to create the new configuration
    response = make_requests_call(
        method='post',
        endpoint=f'workspaces/{tfe_workspace}/configuration-versions',
        data={
            'data': {
                'type': 'configuration-versions',
                'attributes': {'auto-queue-runs': 'true'}
            }
        }
    )

    # upload configuration and trigger a workspace run
    return upload_configuration(
        source_dir=render_dir,
        upload_url=response['data']['attributes']['upload-url'],
        upload_file=config_file
    )
