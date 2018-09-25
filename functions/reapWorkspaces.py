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

def grabWorkspaceDetails(URL):
    response = json.loads((requests.get(tfeURL + URL,headers=headers)).text)
    return(response)


#Kicks off the Plan to Destroy a workspace.
def destroyWorkspace(workspaceID):
    payload = {
                "data": {
                    "attributes": {
                    "is-destroy":True,
                    "message": "Workspace Destroyed by ReaperBot"
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

def UpdateItem(workspaceId, expressionAttributes):
    try:
        response = table.update_item(
            Key={
                'workspaceId': workspaceId
            },
            UpdateExpression=expression,
            ExpressionAttributeValues={
                expressionAttributes
            },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == "ValidationException":
            table.put_item(
                Item={
                    'workspaceId' : workspaceId,
                    'iterations' : 15
                }
            )
        else:
            raise

def getPolicy(runID):
    policyURL = tfeURL + "/api/v2/runs/" + runID + "/policy-checks"
    response = json.loads(requests.get(policyURL, headers=headers).text)
    print(response)
    return response
def policyOverride(polID):
    policyOverrideURL = tfeURL + "/api/v2/policy-checks/" + polID + "/actions/override"
    response = requests.post(policyOverrideURL,headers=headers)
    print("Policy being overriden")
    print(response.text)

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
                    wsDetails = grabWorkspaceDetails(workspaceURL)
                    if wsDetails['data']['attributes']['locked'] == False:
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
                                'workspaceId' : workspaceID,
                                'status' : 'beginning',
                                'lastStatus' : 'first',
                                'runPayload' : runDetails,
                                'variablePayload' : variable,
                                'workspaceName' : wsDetails['data']['attributes']['name']
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
        print("This is the status: " + status)
        response = table.update_item(
                        Key={
                            'workspaceId': workspaceID
                        },
                        UpdateExpression="SET lastStatus = :l, status = :s",
                        ExpressionAttributeValues={
                            ':l': {'S':lastStatus},
                            ':s': {'S':status}
                        },
                        ReturnValues="UPDATED_NEW"
                    )
        if lastStatus == 'planning' or lastStatus == 'planned' or lastStatus == 'applying':
            if status == 'planning' or status == 'applying':
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 30
                sendMessage(payload,delay)
            elif status == 'planned' or status == 'planned_and_finished':
                applyRun(runID)
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 15
                sendMessage(payload,delay)
            else:
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 5
                sendMessage(payload,delay)
        elif lastStatus == 'policy_checked' or lastStatus == 'policy_override':
            if status == 'policy_override':
                print("Policy Override - Overridding")
                policy = getPolicy(runID)
                policyResult = policy['data'][0]['attributes']['result']['result']
                permCanOverride = policy['data'][0]['attributes']['permissions']['can-override']
                actionCanOverride = policy['data'][0]['attributes']['actions']['is-overridable']
                polID = policy['data'][0]['id']
                if policyResult == True:
                    applyRun(runID)
                    payload = {
                        'workspaceID':workspaceID,'status':status,'runID':runID
                    }
                    delay = 30
                elif policyResult == False:
                    if permCanOverride == True and actionCanOverride == True:
                        policyOverride(polID)
                        payload = {
                        'workspaceID':workspaceID,'status':status,'runID':runID
                        }
                        delay = 5   
                sendMessage(payload,delay)
            elif status == 'policy_checked':
                print("Policy Checked - Applying Run")
                applyRun(runID)
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 30
                sendMessage(payload,delay)
            elif status == 'applying':
                payload = {
                    'workspaceID':workspaceID,'status':status,'runID':runID
                }
                delay = 30
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
        elif lastStatus == "errored":
            response = table.update_item(
                        Key={
                            'workspaceId': workspaceID
                        },
                        UpdateExpression="SET lastStatus = :l, status = :s",
                        ExpressionAttributeValues={
                            ':l': {'S':lastStatus},
                            ':s': {'S':'errored'}
                        },
                        ReturnValues="UPDATED_NEW"
                    )

        #Delete the message as it has been processed
        response = sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['receiptHandle']
        )
        print(response)
    return {'status':'Successfully Processed'}