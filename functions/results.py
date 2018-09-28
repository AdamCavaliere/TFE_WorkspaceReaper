import boto3
import os
from boto3.dynamodb.conditions import Key, Attr
import json
import decimal



org = os.environ["TFE_ORG"]
dyn = boto3.resource('dynamodb')
table = dyn.Table('WorkspaceReaper-' + org)

def getSavings():
    savings = table.get_item(
        Key={
            'workspaceId': 'orgSavings'
        }
    )
    destructions = savings['Item']['destructions']
    return destructions

def getWorkspaces():
    workspaces = table.scan(
        FilterExpression=Attr('workspaceId').contains('ws-')
    )
    return workspaces['Items']

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def pullDetails(json_input, context):
    destructions = getSavings()
    workspaces = getWorkspaces()
    details = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {'type':'application/json'},
        'body': {'destructions': int(destructions), 'workspaces': workspaces}
    }
    return json.dumps(details,cls=DecimalEncoder)

    

#print(json.dumps(pullDetails("blah","blah"),cls=DecimalEncoder))