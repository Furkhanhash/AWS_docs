import boto3
from datetime import datetime
from pytz import timezone


def ec2_change(status,ids):
    if status=="start":
        response=ec2.stop_instances(InstanceIds=[s])
        print(response)


# Initialize a session using Boto3
#session = boto3.Session(region_name='us-east-1')
ec2=boto3.client('ec2',region_name='us-east-2')
# Initialize an S3 client
#s3 = session.client('s3')
s="i-0ed2425feb3013168"


tz=timezone('US/Eastern')
current_t=datetime.now(tz)


dw=current_t.isoweekday()

if dw==2:
    ec2_change("start",s)
elif dw==4:
    print("Here")


# List all buckets
#response = s3.list_buckets()

# Print the bucket names
#for bucket in response['Buckets']:
#    print(bucket['Name'])
