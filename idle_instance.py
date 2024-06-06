import boto3
from datetime import datetime
from pytz import timezone


def ec2_change(status, ids):
    ec2 = boto3.client('ec2', region_name='us-east-2')
    if status == "start":
        response = ec2.start_instances(InstanceIds=ids)
    elif status == "stop":
        response = ec2.stop_instances(InstanceIds=ids)
    return response


def ec2_optimize(event, context):
    s = ["i-0ed2425feb3013168", "i-020d74232cc101f04"]
    tz = timezone('US/Eastern')
    current_t = datetime.now(tz)
    dw = current_t.isoweekday()
    print(dw)
    if dw == 1:  # Monday
        ec2_change("start", s)
    elif dw == 5:  # Friday
        ec2_change("stop", s)


if __name__ == "__main__":
    ec2_optimize(None, None)
