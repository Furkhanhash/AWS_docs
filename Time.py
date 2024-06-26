import argparse
import logging
from datetime import datetime, time
from pytz import timezone
from common import load_schedule, get_client
from ec2_management import get_instances_with_schedule_tag, manage_ec2_instances
from rds_management import get_rds_clusters_with_schedule_tag, get_rds_instances_with_schedule_tag, manage_rds_clusters, manage_rds_instances

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

def should_perform_action(plan_name, current_time, schedule_data):
    schedule = schedule_data[plan_name]
    tz = timezone(schedule['timezone'])
    current_time = current_time.astimezone(tz)
    start_time = time.fromisoformat(schedule['start_time'])
    stop_time = time.fromisoformat(schedule['stop_time'])
    
    if current_time.weekday() + 1 in schedule['start_days']:
        if start_time <= current_time.time() < stop_time:
            return 'start'
    if current_time.weekday() + 1 in schedule['stop_days']:
        if stop_time <= current_time.time() or current_time.time() < start_time:
            return 'stop'
    return None

def manage_instances(scan_ec2, scan_rds):
    schedule_data = load_schedule('schedule.json')
    tag_key = 'schedule'
    tag_value = 'on'
    regions = ['us-east-1', 'us-west-1', 'us-west-2']

    all_ec2_instances = []
    all_rds_clusters = []
    all_rds_instances = []

    for region in regions:
        if scan_ec2:
            ec2_client = get_client('ec2', region)
            logger.info(f"Checking EC2 instances in region: {region}")
            ec2_instances = get_instances_with_schedule_tag(ec2_client, tag_key, tag_value)
            logger.info(f"EC2 instances in {region}: {ec2_instances}")
            all_ec2_instances.extend(ec2_instances)

        if scan_rds:
            rds_client = get_client('rds', region)
            logger.info(f"Checking RDS clusters in region: {region}")
            rds_clusters = get_rds_clusters_with_schedule_tag(rds_client, tag_key, tag_value)
            logger.info(f"RDS clusters in {region}: {rds_clusters}")
            all_rds_clusters.extend(rds_clusters)

            logger.info(f"Checking RDS instances in region: {region}")
            rds_instances = get_rds_instances_with_schedule_tag(rds_client, tag_key, tag_value)
            logger.info(f"RDS instances in {region}: {rds_instances}")
            all_rds_instances.extend(rds_instances)

    if scan_ec2:
        logger.info(f"All EC2 instances: {all_ec2_instances}")
    if scan_rds:
        logger.info(f"All RDS clusters: {all_rds_clusters}")
        logger.info(f"All RDS instances: {all_rds_instances}")

    if not all_ec2_instances and not all_rds_clusters and not all_rds_instances:
        logger.info(f'No instances or clusters found with tag {tag_key}.')
        return

    now = datetime.now(timezone('UTC'))

    for instance_id, region, plan_name, state in all_ec2_instances:
        action = should_perform_action(plan_name, now, schedule_data)
        ec2_client = get_client('ec2', region)
        if action == 'start' and state == 'stopped':
            start_ec2_instances(ec2_client, [instance_id])
        elif action == 'stop' and state == 'running':
            stop_ec2_instances(ec2_client, [instance_id])

    for cluster_id, region, plan_name, status in all_rds_clusters:
        rds_client = get_client('rds', region)
        action = should_perform_action(plan_name, now, schedule_data)
        if action == 'start' and status == 'stopped':
            start_rds_cluster(rds_client, cluster_id)
        elif action == 'stop' and status == 'available':
            stop_rds_cluster(rds_client, cluster_id)

    for instance_id, region, plan_name, status in all_rds_instances:
        rds_client = get_client('rds', region)
        action = should_perform_action(plan_name, now, schedule_data)
        if action == 'start' and status == 'stopped':
            start_rds_instance(rds_client, instance_id)
        elif action == 'stop' and status == 'available':
            stop_rds_instance(rds_client, instance_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage AWS EC2 and RDS instances based on schedule.")
    parser.add_argument("--ec2", action="store_true", help="Scan and manage EC2 instances")
    parser.add_argument("--rds", action="store_true", help="Scan and manage RDS clusters and instances")

    args = parser.parse_args()
    scan_ec2 = args.ec2
    scan_rds = args.rds

    # If no arguments are provided, scan both EC2 and RDS
    if not scan_ec2 and not scan_rds:
        scan_ec2 = scan_rds = True

    manage_instances(scan_ec2, scan_rds)
