import boto3
import logging
from botocore.client import BaseClient
from exceptions import AccountListException

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def flatten_iterator(data: list, key_name: str) -> list:
    flattened = []
    for it in data:
        flattened.extend(it[key_name])
    return flattened


def list_accounts(client: BaseClient) -> list:
    paginator = client.get_paginator('list_accounts')
    return flatten_iterator(data=paginator.paginate(), key_name='Accounts')


def get_account_id(client: BaseClient, email: str) -> str:
    accounts = list_accounts(client=client)

    for account in accounts:
        if account['Email'] == email:
            return account['Id']


def lambda_handler(event, context):
    client = boto3.client('organizations')
    acct_email = event["acct_email"]

    if event['acct_describe_request']['results'].get('failure_reason', 'NaN') == 'EMAIL_ALREADY_EXISTS':
        acct_id = get_account_id(client=client, email=acct_email)

        if acct_id is not None:
            response = client.describe_account(AccountId=acct_id)

            return {
                'acct_id': acct_id,
                'acct_arn': response['Account']['Arn'],
                'acct_email': response['Account']['Email'],
                'acct_name': response['Account']['Name'],
                'acct_status': response['Account']['Status'],
                'acct_joined': str(response['Account']['JoinedTimestamp']),
            }
        else:
            raise AccountListException(f'Unable to retrieve details for account with email={acct_email}')
