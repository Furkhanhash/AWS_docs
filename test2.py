import boto3
import logging
from datetime import datetime
from pytz import timezone

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Initialize the STS client for assuming roles
sts_client = boto3.client('sts')

def assume_role(account_id, role_name):
    """
    Assume a role in the specified account and return the temporary credentials.
    """
    role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName='InstanceSchedulerSession'
    )
    return response['Credentials']

def get_client(service, region_name, credentials=None):
    """
    Initialize a boto3 client with optional assumed role credentials for a specific service and region.
    """
    if credentials:
        return boto3.client(
            service,
            region_name=region_name,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
    else:
        return boto3.client(service, region_name=region_name)

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
    instances = [(instance['InstanceId'], ec2_client.meta.region_name, instance['State']['Name']) for reservation in response['Reservations'] for instance in reservation['Instances']]
    return instances

def get_rds_clusters(rds_client, tag_key, tag_value):
    """
    Get all RDS clusters with a specific tag key and value in a specified region.
    """
    response = rds_client.describe_db_clusters()
    clusters = []
    for cluster in response['DBClusters']:
        tags_response = rds_client.list_tags_for_resource(ResourceName=cluster['DBClusterArn'])
        tags = tags_response['TagList']
        if any(tag['Key'] == tag_key and tag['Value'] == tag_value for tag in tags):
            clusters.append((cluster['DBClusterIdentifier'], rds_client.meta.region_name, cluster['Status']))
    return clusters

def start_ec2_instances(ec2_client, instance_ids):
    """
    Start the EC2 instances.
    """
    if instance_ids:
        ec2_client.start_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully started EC2 instances: {instance_ids}')

def stop_ec2_instances(ec2_client, instance_ids):
    """
    Stop the EC2 instances.
    """
    if instance_ids:
        ec2_client.stop_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully stopped EC2 instances: {instance_ids}')

def start_rds_cluster(rds_client, cluster_id):
    """
    Start the RDS cluster.
    """
    try:
        rds_client.start_db_cluster(DBClusterIdentifier=cluster_id)
        logger.info(f'Successfully started RDS cluster: {cluster_id}')
    except Exception as e:
        logger.error(f"Error starting RDS cluster {cluster_id}: {e}")

def stop_rds_cluster(rds_client, cluster_id):
    """
    Stop the RDS cluster.
    """
    try:
        rds_client.stop_db_cluster(DBClusterIdentifier=cluster_id)
        logger.info(f'Successfully stopped RDS cluster: {cluster_id}')
    except Exception as e:
        logger.error(f"Error stopping RDS cluster {cluster_id}: {e}")

def manage_instances(account_id, role_name, regions):
    """
    Manage EC2 and RDS instances in the specified account and regions based on the schedule.
    """
    # Assume role in the member account
    credentials = assume_role(account_id, role_name)

    all_ec2_instances = []
    all_rds_clusters = []
    for region in regions:
        ec2_client = get_client('ec2', region, credentials)
        rds_client = get_client('rds', region, credentials)
        
        logger.info(f"Checking EC2 instances in region: {region}")
        ec2_instances = get_ec2_instances(ec2_client, 'Schedule', 'On')
        logger.info(f"EC2 instances in {region}: {ec2_instances}")
        all_ec2_instances.extend(ec2_instances)
        
        logger.info(f"Checking RDS clusters in region: {region}")
        rds_clusters = get_rds_clusters(rds_client, 'Schedule', 'On')
        logger.info(f"RDS clusters in {region}: {rds_clusters}")
        all_rds_clusters.extend(rds_clusters)

    logger.info(f"All EC2 instances: {all_ec2_instances}")
    logger.info(f"All RDS clusters: {all_rds_clusters}")
    if not all_ec2_instances and not all_rds_clusters:
        logger.info(f'No instances or clusters found with tag Schedule=On.')
        return

    # Determine the action based on the current day
    tz = timezone('US/Eastern')
    current_t = datetime.now(tz)
    dw = current_t.isoweekday()

    action = 'start' if dw in range(1, 6) else 'stop'  # Start on weekdays, stop on weekends

    # Start or stop instances based on the determined action
    for instance_id, region, state in all_ec2_instances:
        ec2_client = get_client('ec2', region, credentials)
        if action == 'start' and state == 'stopped':
            start_ec2_instances(ec2_client, [instance_id])
        elif action == 'stop' and state == 'running':
            stop_ec2_instances(ec2_client, [instance_id])

    for cluster_id, region, status in all_rds_clusters:
        rds_client = get_client('rds', region, credentials)
        if action == 'start' and status == 'stopped':
            start_rds_cluster(rds_client, cluster_id)
        elif action == 'stop' and status == 'available':
            stop_rds_cluster(rds_client, cluster_id)

    logger.info(f'Successfully performed {action} action on EC2 instances: {all_ec2_instances}')
    logger.info(f'Successfully performed {action} action on RDS clusters: {all_rds_clusters}')

if __name__ == "__main__":
    # List of member account IDs, the role name to assume, and regions
    accounts = ['123456789012', '234567890123']  # Replace with actual account IDs
    role_name = 'EC2SchedulerRole'  # Replace with the actual role name
    regions = ['us-east-1', 'us-west-1', 'us-west-2']  # Replace with desired regions

    for account_id in accounts:
        manage_instances(account_id, role_name, regions)
