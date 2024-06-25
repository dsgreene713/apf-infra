import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    client = boto3.client('organizations')
    request_id = event['acct_create']['results']['request_id']

    try:
        logger.info(f'create account request id: {request_id}')
        response = client.describe_create_account_status(CreateAccountRequestId=request_id)
    except ClientError as ex:
        logger.warning(ex.response['Error']['Code'])
        logger.warning(ex.response['Error']['Message'])
        raise ex

    return {
        'acct_name': response.get('CreateAccountStatus', {}).get('AccountName', 'NaN'),
        'acct_id': response.get('CreateAccountStatus', {}).get('AccountId', 'NaN'),
        'state': response.get('CreateAccountStatus', {}).get('State', 'NaN'),
        'creation_date': str(response.get('CreateAccountStatus', {}).get('CompletedTimestamp', 'NaN')),
        'failure_reason': response.get('CreateAccountStatus', {}).get('FailureReason', 'NaN'),
    }
