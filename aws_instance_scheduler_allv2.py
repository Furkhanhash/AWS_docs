import boto3
import logging
import json
from datetime import datetime
from pytz import timezone

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

def load_schedule(file_path='schedule.json'):
    with open(file_path, 'r') as file:
        return json.load(file)

def get_client(service, region_name):
    return boto3.client(service, region_name=region_name)

def get_instances_with_schedule_tag(ec2_client, tag_key, tag_value):
    filters = [{'Name': f'tag:{tag_key}', 'Values': [tag_value]}]
    response = ec2_client.describe_instances(Filters=filters)
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            schedule_on = False
            plan_name = None
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Schedule' and tag['Value'] == 'On':
                    schedule_on = True
                if tag['Key'] == 'Plan':
                    plan_name = tag['Value']
            if schedule_on and plan_name:
                instances.append((instance['InstanceId'], ec2_client.meta.region_name, plan_name, instance['State']['Name']))
    return instances

def get_rds_clusters_with_schedule_tag(rds_client, tag_key, tag_value):
    response = rds_client.describe_db_clusters()
    clusters = []
    for cluster in response['DBClusters']:
        schedule_on = False
        plan_name = None
        tags_response = rds_client.list_tags_for_resource(ResourceName=cluster['DBClusterArn'])
        for tag in tags_response['TagList']:
            if tag['Key'] == 'Schedule' and tag['Value'] == 'On':
                schedule_on = True
            if tag['Key'] == 'Plan':
                plan_name = tag['Value']
        if schedule_on and plan_name:
            clusters.append((cluster['DBClusterIdentifier'], rds_client.meta.region_name, plan_name, cluster['Status']))
    return clusters

def get_rds_instances_with_schedule_tag(rds_client, tag_key, tag_value):
    response = rds_client.describe_db_instances()
    instances = []
    for instance in response['DBInstances']:
        schedule_on = False
        plan_name = None
        tags_response = rds_client.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])
        for tag in tags_response['TagList']:
            if tag['Key'] == 'Schedule' and tag['Value'] == 'On':
                schedule_on = True
            if tag['Key'] == 'Plan':
                plan_name = tag['Value']
        if schedule_on and plan_name:
            instances.append((instance['DBInstanceIdentifier'], rds_client.meta.region_name, plan_name, instance['DBInstanceStatus']))
    return instances

def start_ec2_instances(ec2_client, instance_ids):
    if instance_ids:
        ec2_client.start_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully started EC2 instances: {instance_ids}')

def stop_ec2_instances(ec2_client, instance_ids):
    if instance_ids:
        ec2_client.stop_instances(InstanceIds=instance_ids)
        logger.info(f'Successfully stopped EC2 instances: {instance_ids}')

def start_rds_cluster(rds_client, cluster_id):
    try:
        rds_client.start_db_cluster(DBClusterIdentifier=cluster_id)
        logger.info(f'Successfully started RDS cluster: {cluster_id}')
    except Exception as e:
        logger.error(f"Error starting RDS cluster {cluster_id}: {e}")

def stop_rds_cluster(rds_client, cluster_id):
    try:
        rds_client.stop_db_cluster(DBClusterIdentifier=cluster_id)
        logger.info(f'Successfully stopped RDS cluster: {cluster_id}')
    except Exception as e:
        logger.error(f"Error stopping RDS cluster {cluster_id}: {e}")

def start_rds_instance(rds_client, instance_id):
    try:
        rds_client.start_db_instance(DBInstanceIdentifier=instance_id)
        logger.info(f'Successfully started RDS instance: {instance_id}')
    except Exception as e:
        logger.error(f"Error starting RDS instance {instance_id}: {e}")

def stop_rds_instance(rds_client, instance_id):
    try:
        rds_client.stop_db_instance(DBInstanceIdentifier=instance_id)
        logger.info(f'Successfully stopped RDS instance: {instance_id}')
    except Exception as e:
        logger.error(f"Error stopping RDS instance {instance_id}: {e}")

def get_action(schedule, current_day, current_time):
    for key, value in schedule.items():
        if current_day in value['start_days'] and current_time == value['start_time']:
            return 'start'
        if current_day in value['stop_days'] and current_time == value['stop_time']:
            return 'stop'
    return None

def manage_instances():
    schedule = load_schedule()
    tag_key = 'Schedule'
    tag_value = 'On'
    regions = ['us-east-1', 'us-west-1', 'us-west-2']

    all_ec2_instances = []
    all_rds_clusters = []
    all_rds_instances = []

    for region in regions:
        ec2_client = get_client('ec2', region)
        rds_client = get_client('rds', region)
        
        logger.info(f"Checking EC2 instances in region: {region}")
        ec2_instances = get_instances_with_schedule_tag(ec2_client, tag_key, tag_value)
        logger.info(f"EC2 instances in {region}: {ec2_instances}")
        all_ec2_instances.extend(ec2_instances)
        
        logger.info(f"Checking RDS clusters in region: {region}")
        rds_clusters = get_rds_clusters_with_schedule_tag(rds_client, tag_key, tag_value)
        logger.info(f"RDS clusters in {region}: {rds_clusters}")
        all_rds_clusters.extend(rds_clusters)
        
        logger.info(f"Checking RDS instances in region: {region}")
        rds_instances = get_rds_instances_with_schedule_tag(rds_client, tag_key, tag_value)
        logger.info(f"RDS instances in {region}: {rds_instances}")
        all_rds_instances.extend(rds_instances)

    logger.info(f"All EC2 instances: {all_ec2_instances}")
    logger.info(f"All RDS clusters: {all_rds_clusters}")
    logger.info(f"All RDS instances: {all_rds_instances}")
    if not all_ec2_instances and not all_rds_clusters and not all_rds_instances:
        logger.info(f'No instances or clusters found with tag {tag_key}.')
        return

    tz = timezone('US/Eastern')
    current_t = datetime.now(tz)
    current_day = current_t.isoweekday()
    current_time = current_t.strftime('%H:%M')

    for instance_id, region, plan_name, state in all_ec2_instances:
        ec2_client = get_client('ec2', region)
        if plan_name in schedule:
            action = get_action(schedule[plan_name], current_day, current_time)
            if action == 'start' and state == 'stopped':
                start_ec2_instances(ec2_client, [instance_id])
            elif action == 'stop' and state == 'running':
                stop_ec2_instances(ec2_client, [instance_id])

    for cluster_id, region, plan_name, status in all_rds_clusters:
        rds_client = get_client('rds', region)
        if plan_name in schedule:
            action = get_action(schedule[plan_name], current_day, current_time)
            if action == 'start' and status == 'stopped':
                start_rds_cluster(rds_client, cluster_id)
            elif action == 'stop' and status == 'available':
                stop_rds_cluster(rds_client, cluster_id)
    
    for instance_id, region, plan_name, status in all_rds_instances:
        rds_client = get_client('rds', region)
        if plan_name in schedule:
            action = get_action(schedule[plan_name], current_day, current_time)
            if action == 'start' and status == 'stopped':
                start_rds_instance(rds_client, instance_id)
            elif action == 'stop' and status == 'available':
                stop_rds_instance(rds_client, instance_id)

    logger.info(f'Successfully managed instances based on schedule.')

if __name__ == "__main__":
    manage_instances()
