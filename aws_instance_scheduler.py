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

def get_client(service, region_name):
    """
    Initialize a boto3 client with hardcoded credentials for a specific service and region.
    """
    return boto3.client(
        service,
        region_name=region_name,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN  # Optional if you have a session token
    )

def get_ec2_instances(ec2_client, tag_key, tag_value):
    """
    Get all EC2 instances with a specific tag key and value in a specified region.
    """
    filters = [
        {
            'Name': f'tag:{tag_key}',
            'Values': [tag_value]
        }
    ]
    response = ec2_client.describe_instances(Filters=filters)
    instances = [(instance['InstanceId'], ec2_client.meta.region_name) for reservation in response['Reservations'] for instance in reservation['Instances']]
    return instances

def get_rds_instances(rds_client, tag_key, tag_value):
    """
    Get all RDS instances with a specific tag key and value in a specified region.
    """
    response = rds_client.describe_db_instances()
    instances = []
    for db_instance in response['DBInstances']:
        tags = rds_client.list_tags_for_resource(ResourceName=db_instance['DBInstanceArn'])['TagList']
        if any(tag['Key'] == tag_key and tag['Value'] == tag_value for tag in tags):
            instances.append((db_instance['DBInstanceIdentifier'], rds_client.meta.region_name))
    return instances

def start_instances(ec2_client, instance_ids):
    """
    Start the EC2 instances.
    """
    if instance_ids:
        ec2_client.start_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully started EC2 instances: {instance_ids}')

def stop_instances(ec2_client, instance_ids):
    """
    Stop the EC2 instances.
    """
    if instance_ids:
        ec2_client.stop_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully stopped EC2 instances: {instance_ids}')

def start_rds_instances(rds_client, instance_ids):
    """
    Start the RDS instances.
    """
    if instance_ids:
        for instance_id in instance_ids:
            rds_client.start_db_instance(DBInstanceIdentifier=instance_id)
        logger.info(f'Successfully started RDS instances: {instance_ids}')

def stop_rds_instances(rds_client, instance_ids):
    """
    Stop the RDS instances.
    """
    if instance_ids:
        for instance_id in instance_ids:
            rds_client.stop_db_instance(DBInstanceIdentifier=instance_id)
        logger.info(f'Successfully stopped RDS instances: {instance_ids}')

def manage_instances():
    """
    Manage EC2 and RDS instances based on the schedule.
    """
    tag_key = 'Schedule'
    tag_value = 'On'
    regions = ['us-east-1', 'us-west-1', 'us-west-2']  # Add the regions you want to check

    all_ec2_instances = []
    all_rds_instances = []
    for region in regions:
        ec2_client = get_client('ec2', region)
        rds_client = get_client('rds', region)
        ec2_instances = get_ec2_instances(ec2_client, tag_key, tag_value)
        rds_instances = get_rds_instances(rds_client, tag_key, tag_value)
        all_ec2_instances.extend(ec2_instances)
        all_rds_instances.extend(rds_instances)

    print("EC2 Instances:", all_ec2_instances)
    print("RDS Instances:", all_rds_instances)
    if not all_ec2_instances and not all_rds_instances:
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
    for instance_id, region in all_ec2_instances:
        ec2_client = get_client('ec2', region)
        if action == 'start':
            start_instances(ec2_client, [instance_id])
        elif action == 'stop':
            stop_instances(ec2_client, [instance_id])

    for instance_id, region in all_rds_instances:
        rds_client = get_client('rds', region)
        if action == 'start':
            start_rds_instances(rds_client, [instance_id])
        elif action == 'stop':
            stop_rds_instances(rds_client, [instance_id])

    logger.info(f'Successfully performed {action} action on EC2 instances: {all_ec2_instances}')
    logger.info(f'Successfully performed {action} action on RDS instances: {all_rds_instances}')

if __name__ == "__main__":
    manage_instances()
