import logging
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Define your account configuration
# accounts = {
#     "dummy11": "dsgreene713+dummy11@gmail.com",
# }

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('accounts_template.j2')


def lambda_handler(event, context):
    accounts = {}
    output = template.render(accounts=accounts)
    tf_file = 'dynamic_accounts.tf'

    with open(tf_file, 'w') as f:
        f.write(output)

    logger.info(f'successfully generated {tf_file}')
    return {'statusCode': 200}
