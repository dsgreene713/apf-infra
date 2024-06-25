import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


account_tags = [
    {
        'Key': 'provisioned-by',
        'Value': 'apf-pipeline'
    },
]


def lambda_handler(event, context):
    client = boto3.client('organizations')
    acct_email = event['acct_email']
    acct_name = event['acct_name']
    acct_owner = event.get('acct_owner', 'Unspecified')
    tags = event.get('acct_tags', [])

    try:
        logger.info(f'submitting account request for {acct_owner}: acct_email={acct_email}, acct_name={acct_name}')
        account_tags.extend([{'Key': 'provisioned-for', 'Value': acct_owner}])
        account_tags.extend(tags)

        response = client.create_account(
            Email=acct_email,
            AccountName=acct_name,
            RoleName='APFLaunchPadAdminRole',
            IamUserAccessToBilling='ALLOW',
            # Tags=account_tags
        )
    except ClientError as ex:
        logger.error(ex.response['Error']['Code'])
        logger.error(ex.response['Error']['Message'])
        raise ex

    return {
        'request_id': response['CreateAccountStatus']['Id'],
        'state': response['CreateAccountStatus']['State'],
    }
