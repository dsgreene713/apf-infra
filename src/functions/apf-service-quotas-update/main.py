import logging

import boto3
import yaml
from botocore.client import BaseClient, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def flatten_iterator(data: list, key_name: str) -> list:
    flattened = []
    for it in data:
        flattened.extend(it[key_name])
    return flattened


def update_service_quotas(client: BaseClient, service: str, quota_code: str, value: int):
    try:
        response = client.request_service_quota_increase(
            ServiceCode=service,
            QuotaCode=quota_code,
            DesiredValue=value,
        )
        return response['RequestedQuota']['Status']
    except ClientError as ex:
        error_code = ex.response['Error']['Code']
        error_message = ex.response['Error']['Message']

        if error_code == 'IllegalArgumentException' and ('You must provide a quota value greater than the current '
                                                         'quota value') in error_message:
            pass
        else:
            logger.warning(error_code)
            logger.warning(error_message)
            raise ex


def get_pending_service_quota_requests(client: BaseClient, service: str):
    paginator = client.get_paginator('list_requested_service_quota_change_history')
    pending_statuses = ['PENDING',  'CASE_OPENED', 'APPROVED']

    requests = flatten_iterator(paginator.paginate(
        ServiceCode=service,
        QuotaRequestedAtLevel='ALL'),
        key_name='RequestedQuotas'
    )

    return [request['QuotaCode'] for request in requests if request['Status'] in pending_statuses]


def lambda_handler(event, context):
    with open('service-quota-config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    client = boto3.client('service-quotas')
    results = {}

    for service, quotas in config['ServiceQuotas'].items():
        pending = get_pending_service_quota_requests(client=client, service=service)
        results[service] = []

        for quota in quotas:
            quota_code = quota['QuotaCode']
            new_value = quota['DesiredValue']

            if quota_code not in pending:
                status = update_service_quotas(
                    client=client,
                    service=service,
                    quota_code=quota_code,
                    value=new_value
                )
                results[service].append({'QuotaCode': quota_code, 'Status': status})
                logging.info(f'updated service={service}, quota code={quota_code} to {new_value}')
            else:
                results[service].append({'QuotaCode': quota_code, 'Status': 'PENDING'})
                logging.info(f'skipping service={service}, quota code={quota_code}: already pending.')

    return results
