import boto3
import os
from boto3.dynamodb.conditions import Key, Attr
from flask import (
    Flask,
    jsonify,
    render_template
)
app = Flask(__name__)



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

@app.route('/')
def resourcesDestroyed():
    return render_template('index.html', destructions=getSavings(), workspaces=getWorkspaces()
    )

def lambda_handler(event,context):
    return awsgi.response(app,event,context)

app.run(host="0.0.0.0")