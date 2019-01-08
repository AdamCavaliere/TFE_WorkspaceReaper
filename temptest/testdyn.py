import os
import boto3
import decimal
from botocore.exceptions import ClientError

org = "azc"

dyn = boto3.resource('dynamodb')
table = dyn.Table('WorkspaceReaper-' + org)

#response = table.get_item(Key={'workspaceId':'orgSavings'})

try:
    response = table.update_item(
        Key={
            'workspaceId': 'orgSavings'
        },
        UpdateExpression="set destructions = destructions + :val",
        ExpressionAttributeValues={
            ':val': 5
        },
        ReturnValues="UPDATED_NEW"
    )
except ClientError as e:
    if e.response['Error']['Code'] == "ValidationException":
        table.put_item(
            Item={
                'workspaceId' : 'orgSavings',
                'destructions' : 5
            }
        )
    else:
        raise