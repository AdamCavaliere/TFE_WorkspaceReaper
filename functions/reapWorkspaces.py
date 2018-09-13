import requests
import os
import json
from datetime import datetime, timedelta
import time
import boto3

sqs = boto3.client('sqs')
tfeURL = os.environ["TFE_URL"]
org = os.environ["TFE_ORG"]
AtlasToken = os.environ["TFE_TOKEN"]
headers = {'Authorization': "Bearer " + AtlasToken, 'Content-Type' : 'application/vnd.api+json'}
getWorkspaces_URL = tfeURL + "/api/v2/organizations/" + org + "/workspaces"
queue_url = os.environ["SQS_QUEUE"]


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

def runStatus(workspaceID,runID):
    runURL = tfeURL + "/api/v2/workspaces/" + workspaceID + "/runs?status=applied"
    runPayloads = json.loads((requests.get(runURL, headers=headers)).text)
    for runPayload in runPayloads['data']:
            if runPayload['id'] == runID:
                return(runPayload)    

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

def getPlanStatus(planID):
    planURL = tfeURL + "/api/v2/plans/" + planID
    response = json.loads(requests.get(planURL, headers=headers).text)
    return response

def applyRun(runID):
    applyURL = tfeURL + "/api/v2/runs/" + runID + "/actions/apply"
    response = requests.post(applyURL, headers=headers)
    print(response.text)
    
def sendMessage(payload,attributes):
    response = sqs.send_message(
    MessageBody=json.dumps(payload),
    QueueUrl=queue_url,
    DelaySeconds=10,
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
                    sendMessage(payload)
    return {"status":"Success"}

def processQueue(json_input, context):
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'All'
        ],
        MaxNumberOfMessages=10,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    for message in response['Messages']:
        print(message)
    # runPayload = runStatus(workspaceID,runID)
    # status = runPayload['attributes']['status']
    # keepRunning = True
    # while keepRunning == True:
    #     if status != 'planned':
    #         keepRunning = True
    #         runPayload = runStatus(workspaceID,runID)
    #         status = runPayload['attributes']['status']
    #         print("Still processing...")
    #         time.sleep(5)
    #     else:
    #         applyRun(runID)
    #         print("Applying!")
    #         keepRunning = False