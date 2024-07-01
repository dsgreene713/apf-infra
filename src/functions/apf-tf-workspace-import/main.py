import os
from pathlib import Path
import tarfile
import boto3
import json
import requests
from requests.exceptions import HTTPError
import logging
from jinja2 import Environment, FileSystemLoader

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


def lambda_handler(event, context):
    tfe_workspace = os.environ['TFE_ACCT_IMPORT_WORKSPACE']
    render_dir = os.path.join(os.environ['BASE_OUTPUT_PATH'], 'tf_import')
    rendered_tf_file = 'import_accounts.tf'
    render_template(data=get_template_data(), output_dir=render_dir, tf_file=rendered_tf_file)
    gzip_file = os.path.join(render_dir, 'import_accounts.tar.gz')
    make_tarfile(output='import_accounts.tar.gz', source_dir=render_dir, source_files=[rendered_tf_file])

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

    upload_url = response['data']['attributes']['upload-url']
    upload = {'file': (gzip_file, open(gzip_file, 'rb'), 'application/octet-stream', {'Expires': '0'})}
    logger.info(requests.put(upload_url, files=upload))

    return {
        'status_code': 200
    }
