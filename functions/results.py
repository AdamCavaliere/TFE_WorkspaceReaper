import boto3
import os
from boto3.dynamodb.conditions import Key, Attr




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

def pullDetails():
    destructions = getSavings()
    workspaces = getWorkspaces()
    all = workspaces + destructions
    print(all)
    return jsonify(all)

print(pullDetails())

app.run(host="0.0.0.0")