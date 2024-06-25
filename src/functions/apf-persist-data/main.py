import os
import boto3
import logging
from botocore.exceptions import ClientError
from exceptions import InvalidDataFormat

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def format_data_for_insert(event: dict):
    data = event.get('acct_describe', {}).get('results', {})

    if data:
        return {
            'acct_id': {'S': data['acct_id']},
            'acct_email': {'S': data['acct_email']},
            'acct_name': {'S': data['acct_name']},
            'acct_arn': {'S': data['acct_arn']},
            'acct_status': {'S': data['acct_status']},
            'acct_joined': {'S': data['acct_joined']},
        }
    else:
        error = 'no data provided in event'
        logger.warning(f'{error}:')
        logger.warning(event)
        raise InvalidDataFormat(error)


def lambda_handler(event, context):
    client = boto3.client('dynamodb')
    table = os.environ['DYNAMODB_TABLE']
    data = format_data_for_insert(event=event)

    try:
        client.put_item(TableName=table, Item=data)
        logger.info(f'updated {table} with:')
        logger.info(data)
    except ClientError as ex:
        logger.error(ex.response['Error']['Code'])
        logger.error(ex.response['Error']['Message'])
        raise ex

    return {
        'statusCode': 200,
    }
