import requests
import os
import json
from datetime import datetime, timedelta
import time
import boto3
import logging
import decimal
from botocore.exceptions import ClientError


#Configure SQS Object
sqs = boto3.client('sqs')
queue_url = os.environ["SQS_QUEUE"]

#TFE Variables - set in the Terraform Code, which inputs them into the Lambda Function
tfeURL = os.environ["TFE_URL"]
org = os.environ["TFE_ORG"]
AtlasToken = os.environ["TFE_TOKEN"]

#Configure DynamoDB
dyn = boto3.resource('dynamodb')
table = dyn.Table('WorkspaceReaper-' + org)

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
                break
    
    return lastGoodApply

#Get the current run status - requires the workspaceID, and the runID to pull this.
def runStatus(workspaceID,runID):
    runURL = tfeURL + "/api/v2/workspaces/" + workspaceID + "/runs?status=applied"
    runPayloads = json.loads((requests.get(runURL, headers=headers)).text)
    for runPayload in runPayloads['data']:
            if runPayload['id'] == runID:
                return(runPayload)    

def grabWorkspaceName(URL):
    response = json.loads((requests.get(URL,headers=headers)).text)
    return(response['data']['attributes']['name']


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
    

def sendMessage(payload,delay):
    response = sqs.send_message(
    MessageBody=json.dumps(payload),
    QueueUrl=queue_url,
    DelaySeconds=delay,
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
                    payload = {
                        'workspaceID':workspaceID,'status':"planning",'runID':runID
                    }
                    delay = 5
                    sendMessage(payload,delay)
                    table.put_item(
                        Item={
                            'workspaceId' : workspaceID + "-begin",
                            'status' : 'beginning',
                            'lastStatus' : 'first',
                            'runPayload' : runDetails,
                            'variablePayload' : variable,
                            'workspaceName' : grabWorkspaceName(workspaceURL)
                        }
                    )
    return {"status":"Success"}


def processQueue(json_input, context):
    try:
        Messages = json_input['Records']
    except:
        return {'status':'Failed'}
    for message in Messages:
        body = json.loads(message['body'])
        workspaceID = body['workspaceID']
        runID = body['runID']
        lastStatus = body['status']
        runPayload = runStatus(workspaceID,runID)
        status = runPayload['attributes']['status']
        table.put_item(
            Item={
                'workspaceId' : workspaceID,
                'status' : status,
                'lastStatus' : lastStatus,
                'runPayload' : runPayload
            }
        )
        if lastStatus == 'planning' or lastStatus == 'planned' or lastStatus == 'planned_and_finished':
            if status == 'planning':
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 90
                sendMessage(payload,delay)
            elif status == 'planned' or status == 'planned_and_finished':
                applyRun(runID)
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 90
                sendMessage(payload,delay)
            else:
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 5
                sendMessage(payload,delay)
        elif lastStatus == "applied" or lastStatus == "discarded":
            planDetails = getPlanStatus(runPayload['relationships']['plan']['data']['id'])
            planStatus = planDetails['data']['attributes']['status']
            resourceDestructions = planDetails['data']['attributes']['resource-destructions']
            if planStatus == "finished":
                try:
                    response = table.update_item(
                        Key={
                            'workspaceId': 'orgSavings'
                        },
                        UpdateExpression="set destructions = destructions + :val",
                        ExpressionAttributeValues={
                            ':val': resourceDestructions
                        },
                        ReturnValues="UPDATED_NEW"
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] == "ValidationException":
                        table.put_item(
                            Item={
                                'workspaceId' : 'orgSavings',
                                'destructions' : resourceDestructions
                            }
                        )
                    else:
                        raise
        else:
            payload = {
                'workspaceID':workspaceID,'status':status,'runID':runID
            }
            delay = 10
            sendMessage(payload,delay)
        response = sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['receiptHandle']
        )
    return {'status':'Successfully Processed'}