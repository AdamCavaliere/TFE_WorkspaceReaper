import boto3
import os
from boto3.dynamodb.conditions import Key, Attr
from flask import Flask, render_template
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

workspaces = table.scan(
    FilterExpression=Attr('workspaceId').contains('ws-')
)


print(workspaces)

@app.route('/')
def resourcesDestroyed():
    return render_template('index.html', destructions=getSavings()
    )

app.run(host='0.0.0.0', port=8080, debug=True)
