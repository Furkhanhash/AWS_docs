import boto3
import os
import logging
from datetime import datetime
from pytz import timezone

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Define the regions to manage
regions = ['us-east-1','us-east-2']

def get_ec2_instances(ec2, tag_key, tag_value):
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

def start_instances(ec2, instance_ids):
    """
    Start the EC2 instances.
    """
    if instance_ids:
        ec2.start_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully started instances: {instance_ids}')

def stop_instances(ec2, instance_ids):
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
    tag_key = os.getenv('TAG_KEY', 'Schedule')
    tag_value = os.getenv('TAG_VALUE', 'On')

    tz = timezone('US/Eastern')
    current_t = datetime.now(tz)
    dw = current_t.isoweekday()

    action = 'stop' if dw in [6, 7] else 'start'

    for region in regions:
        ec2 = boto3.client('ec2', region_name=region)
        instance_ids = get_ec2_instances(ec2, tag_key, tag_value)
        
        if not instance_ids:
            logger.info(f'No instances found with tag {tag_key}={tag_value} in region {region}.')
            continue

        # Start or stop instances based on the determined action
        if action == 'start':
            start_instances(ec2, instance_ids)
        elif action == 'stop':
            stop_instances(ec2, instance_ids)

        logger.info(f'Successfully performed {action} action on instances: {instance_ids} in region {region}')

if __name__ == "__main__":
    manage_instances()
