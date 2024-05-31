import boto3
import logging
from datetime import datetime
from pytz import timezone

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Hardcoded AWS credentials (not recommended for production)
AWS_ACCESS_KEY_ID = 'your_access_key_id'
AWS_SECRET_ACCESS_KEY = 'your_secret_access_key'
AWS_SESSION_TOKEN = 'your_session_token'  # Optional if you have a session token

# Initialize the EC2 client with hardcoded credentials
ec2 = boto3.client(
    'ec2',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN  # Optional if you have a session token
)

def get_ec2_instances(tag_key, tag_value):
    """
    Get all EC2 instances with a specific tag key and value.
    """
    filters = [
        {
            'Name': f'tag:{tag_key}',
            'Values': [tag_value]
        }
    ]
    response = ec2.describe_instances(Filters=filters)
    instance_ids = [instance['InstanceId'] for reservation in response['Reservations'] for instance in reservation['Instances']]
    return instance_ids

def start_instances(instance_ids):
    """
    Start the EC2 instances.
    """
    if instance_ids:
        ec2.start_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully started instances: {instance_ids}')

def stop_instances(instance_ids):
    """
    Stop the EC2 instances.
    """
    if instance_ids:
        ec2.stop_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully stopped instances: {instance_ids}')

def manage_instances():
    """
    Manage EC2 instances based on the schedule.
    """
    tag_key = 'Schedule'
    tag_value = 'On'

    instance_ids = get_ec2_instances(tag_key, tag_value)
    print(instance_ids)
    if not instance_ids:
        logger.info(f'No instances found with tag {tag_key}={tag_value}.')
        return

    # Determine the action based on the current day
    tz = timezone('US/Eastern')
    current_t = datetime.now(tz)
    dw = current_t.isoweekday()

    action = None
    if dw in [6, 7]:
        action = 'stop'
    else:
        action = 'start'

    # Start or stop instances based on the determined action
    if action == 'start':
        start_instances(instance_ids)
    elif action == 'stop':
        stop_instances(instance_ids)

    logger.info(f'Successfully performed {action} action on instances: {instance_ids}')

if __name__ == "__main__":
    manage_instances()
