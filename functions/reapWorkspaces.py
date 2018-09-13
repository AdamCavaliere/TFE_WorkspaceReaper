import requests
import os
import json
from datetime import datetime, timedelta
import time
import boto3

#Configure SQS Object
sqs = boto3.client('sqs')
queue_url = os.environ["SQS_QUEUE"]

#TFE Variables - set in the Terraform Code, which inputs them into the Lambda Function
tfeURL = os.environ["TFE_URL"]
org = os.environ["TFE_ORG"]
AtlasToken = os.environ["TFE_TOKEN"]

#Base TFE headers 
headers = {'Authorization': "Bearer " + AtlasToken, 'Content-Type' : 'application/vnd.api+json'}
getWorkspaces_URL = tfeURL + "/api/v2/organizations/" + org + "/workspaces"

#Looking to find the last good run which was applied, not destroyed
def findRuns(workspaceID):
    runURL = tfeURL + "/api/v2/workspaces/" + workspaceID + "/runs?status=applied"
    runPayload = json.loads((requests.get(runURL, headers=headers)).text)
    for run in runPayload['data']:
        if run['attributes']['status'] == "applied":
            if run['attributes']['is-destroy'] == True:
                lastGoodApply = "Destroyed"
                break
            else:
                lastGoodApply = run['attributes']['status-timestamps']['applied-at']
                print(run)
                break
    
    return lastGoodApply

#Get the current run status - requires the workspaceID, and the runID to pull this.
def runStatus(workspaceID,runID):
    runURL = tfeURL + "/api/v2/workspaces/" + workspaceID + "/runs?status=applied"
    runPayloads = json.loads((requests.get(runURL, headers=headers)).text)
    for runPayload in runPayloads['data']:
            if runPayload['id'] == runID:
                return(runPayload)    

#Kicks off the Plan to Destroy a workspace.
def destroyWorkspace(workspaceID):
    payload = {
                "data": {
                    "attributes": {
                    "is-destroy":True,
                    "message": "Custom message"
                    },
                    "type":"runs",
                    "relationships": {
                    "workspace": {
                        "data": {
                        "type": "workspaces",
                        "id": workspaceID
                        }
                    }
                    }
                }
            }
    response = json.loads(requests.post(tfeURL + "/api/v2/runs", headers=headers, data=json.dumps(payload)).text)
    return response

#Not Used at this point
def getPlanStatus(planID):
    planURL = tfeURL + "/api/v2/plans/" + planID
    response = json.loads(requests.get(planURL, headers=headers).text)
    return response
#Kicks off the Apply - there is no response provided.
def applyRun(runID):
    applyURL = tfeURL + "/api/v2/runs/" + runID + "/actions/apply"
    response = requests.post(applyURL, headers=headers)
    

def sendMessage(payload,attributes,delay,receipt_handle="none"):
    response = sqs.send_message(
    MessageBody=json.dumps(payload),
    QueueUrl=queue_url,
    DelaySeconds=delay,
    MessageAttributes=attributes
    )
    if receipt_handle != "none":
        response = client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
        )
    print(response)

def sendMessage2(payload,attributes,delay):
    response = sqs.send_message(
    MessageBody=json.dumps(payload),
    QueueUrl="https://sqs.us-east-2.amazonaws.com/753646501470/temp",
    DelaySeconds=delay,
    MessageAttributes=attributes
    )

def findReapableWorkspaces(json_input, context):
    getVariables_URL = tfeURL + "/api/v2/vars"
    variables = json.loads((requests.get(getVariables_URL, headers=headers)).text)
    for variable in variables['data']:
        if variable['attributes']['key'] == "WORKSPACE_TTL":
            workspaceURL = variable['relationships']['configurable']['links']['related']
            workspaceID = variable['relationships']['configurable']['data']['id']
            runTime = findRuns(workspaceID)
            if runTime != "Destroyed":
                runTimeConverted = datetime.strptime(runTime, "%Y-%m-%dT%H:%M:%S+00:00")
                destroyTime = runTimeConverted + timedelta(minutes=int(variable['attributes']['value']))
                if datetime.now() > destroyTime:
                    print("Lets Do this")
                    runDetails = destroyWorkspace(workspaceID)
                    runID = runDetails['data']['id']
                    attributes = {
                                'run': {
                                    'DataType': 'String',
                                    'StringValue': 'Initial'
                                }
                    }
                    payload = {
                        'workspaceID':workspaceID,'status':"planning",'runID':runID
                    }
                    delay = 30
                    sendMessage(payload,attributes,delay)
    return {"status":"Success"}
attributes2 = {
                    'run': {
                    'DataType': 'String',
                    'StringValue': 'finalizing'
                        }
                }
def processQueue(json_input, context):
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'All'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=10
    )
    try:
        Messages = response['Messages']
    except:
        return {'status':'No Messages'}
    for message in Messages:
        body = json.loads(message['Body'])
        workspaceID = body['workspaceID']
        runID = body['runID']
        lastStatus = body['status']
        receipt_handle = message['ReceiptHandle']
        runPayload = runStatus(workspaceID,runID)
        status = runPayload['attributes']['status']
        payload = {
                    'workspaceID':workspaceID,'status':lastStatus,'runID':runID
                }
        sendMessage2(payload,attributes2,5)
        if lastStatus == 'planning' or lastStatus == 'planned':
            if status == 'planning':
                attributes = {
                    'run': {
                    'DataType': 'String',
                    'StringValue': 'continuing'
                        }
                }
                payload = {
                    'workspaceID':workspaceID,'status':"planning",'runID':runID
                }
                delay = 90
                sendMessage(payload,attributes,delay,receipt_handle)
            elif status == 'planned':
                applyRun(runID)
                attributes = {
                    'run': {
                    'DataType': 'String',
                    'StringValue': 'finalizing'
                        }
                }
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 90
                sendMessage(payload,attributes,delay,receipt_handle)
            else:
                attributes = {
                    'run': {
                    'DataType': 'String',
                    'StringValue': 'finalizing'
                        }
                }
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 5
                sendMessage(payload,attributes,delay,receipt_handle)
        elif lastStatus == "applied" or lastStatus == "discarded":
            print("Done")
    return {'status':'Successfully Processed'}    