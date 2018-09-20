# Terraform Enterprise Workspace Reaper

## Description
This application is utilized to auto-destroy workspaces based on a TTL value being set. 

The application is fully based on Lambda functions, and is automatically deployed via Terraform. 

## Setup

### Configure your TFE Workspace
* Clone this Repo into your VCS
* Set the working directory to be `terraform`
* Configure your TFE Variables

#### Variables Required
 * `TFE_URL` - URL of the Server Instance, e.g. https://app.terraform.io
 * `TFE_ORG` - The organization your workspaces are configured under
 * `TFE_TOKEN` - Either a User Token, or a Team Token


## Resources Utilized
 * AWS - Lambda
 * AWS - SQS
 * AWS - DynamoDB
 * AWS - CloudWatch

![Image of Resources](https://www.lucidchart.com/publicSegments/view/d8cd6d6c-9a05-49ed-8bd9-4e3635b74b87/image.png)

### Lambda
Two functions are deployed:
 * FindWorkspacesToReap-[orgName]
 * ProcessReaperQueue-[orgName]

#### FindWorkspacesToReap
This process loops through the variables in the organization you have specified. It is setup to run every hour, from the time of the deployment of the Lambda function. 

It looks for a specific Key name of `Workspace_TTL`, and an integer value specifying an amount of hours to keep the workspace around. 

For any workspace, which the variable is found in, the process then evaluates whether or not the last run was an apply or destroy. If it was an apply, it then compares the last execution time to the TTL. If the time exceeds the TTL, a message is submitted to the SQS Queue for further processing.

#### ProcessReaperQueue

This process is triggered when a message is submitted to the queue from the FindWorkspacesToReap. It will utilize that message to process the workspace submitted for destruction. It will continue to loop through and process messages until the workspace is finally destroyed.

## Simple Queue Service (SQS)

A single queue is deployed:
 * WorkspaceReaper-[orgName]

This queue is setup to accept messages, and for all messages, there is a delay which keeps the message from being processed. This allows for a limited amount of calls and a variable timing of calls to be made to Terraform Enterprise, based on different factors of planning and applying of workspaces.

## DynamoDB

A single table is created:
 * WorkspaceReaper-[orgName]

This table is utilized for storing details about the workspaces which were destroyed. There is also an item which tracks the amount of resources which have been destroyed. 

## CloudWatch

A single CloudWatch event:
 * WorkspaceReaper-check_hourly-[orgName]

This event fires once an hour to kick off the Lambda function FindWorkspacesToReap

