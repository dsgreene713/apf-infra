import os
import boto3
import json
import requests
import logging
from requests.exceptions import HTTPError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

tfe_base_url = 'https://app.terraform.io/api/v2'


def get_tfe_auth_token():
    client = boto3.client('secretsmanager')
    return client.get_secret_value(SecretId=os.environ['TFE_AUTH_TOKEN_SECRET'])['SecretString']


def get_headers() -> dict:
    return {
        'Authorization': f'Bearer {get_tfe_auth_token()}',
        'Content-Type': 'application/vnd.api+json',
    }


def generate_patch_payload(var_id: str, existing: dict, acct_id: str, acct_email: str, acct_name: str):
    update = {
        acct_id: {
            'acct_email': acct_email,
            'acct_name': acct_name,
        }
    }

    patch = {
        'data': {
            'id': var_id,
            'attributes': {
                'value': existing | update
            },
            'type': 'vars'
        }
    }

    logger.info('patch:')
    logger.info(patch)
    return patch


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


def get_workspace_variables(workspace: str, org_name: str):
    payload = {
        'filter[workspace][name]': workspace,
        'filter[organization][name]': org_name,
    }

    return make_requests_call(method='get', endpoint='vars', payload=payload)


def lambda_handler(event, context):
    tfe_org_name = event['tfe_orginization_name']
    tfe_workspace = event['tfe_workspace']
    workspace_vars = get_workspace_variables(workspace=tfe_workspace, org_name=tfe_org_name)

    for var in workspace_vars['data']:
        tfe_import_var = os.environ['TFE_IMPORT_VAR_NAME']
        existing_value = var['attributes']['value']
        var_name = var['attributes']['key']

        if var_name == tfe_import_var:
            logger.info(f'found tfe import var: {tfe_import_var}')
            logger.info('existing value:')
            logger.info({existing_value})

            payload = generate_patch_payload(
                var_id=var['id'],
                existing=json.loads(var['attributes']['value']),
                acct_id=event['acct_describe']['results']['acct_id'],
                acct_name=event['acct_describe']['results']['acct_name'],
                acct_email=event['acct_describe']['results']['acct_email'],
            )

            return make_requests_call(method='patch', endpoint=f'vars/{var["id"]}', data=payload)
        else:
            logger.info(f'{var_name} does not match {tfe_import_var}')
