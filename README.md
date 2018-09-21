# Terraform Enterprise Workspace Reaper

## Enterprise Benefits

The beauty of Infrastructure as Code with Terraform is that you can specify every piece of infrastructure you need built out. Along with that, the other benefit of Terraform is that you can then destroy all of that infrastructure once you are done with it as well. Some other solutions out there revolve around writing code to destroy individual instances of servers, and potentially other parts of the infrastructure that are deployed, but they don't always catch everything that is deployed. That is where the Workspace Reaper comes into play. It will destroy everything that is configured under a Terraform Workspace. All you have to do is define a variable "WORKSPACE_TTL".

Here is the logic: 
![Decision Tree for Destruction](https://www.lucidchart.com/publicSegments/view/91c993b7-4bb4-4ed7-aa28-82a18feeebb3/image.png)

Conceptually, a [workspace](https://www.terraform.io/docs/enterprise/workspaces/index.html) can be considered a set of infrastructure, tracked by a Terraform state file, which also has many attributes associated with it. Some of these include: [secure variables](https://www.terraform.io/docs/enterprise/workspaces/variables.html), [VCS configurations](https://www.terraform.io/docs/enterprise/vcs/index.html) and even [role based access control](https://www.terraform.io/docs/enterprise/users-teams-organizations/index.html). So not only do we get a secure environment for our variables, but also a secure location that manages the locking of the state as well.

Utilizing Terraform Enterprise (TFE) allows for direct [API integration](https://www.terraform.io/docs/enterprise/api/index.html) for Terraform, which allows a much more rich experience for interacting with Terraform in an automated way. It also allows for us to take advantage of the built in logic that TFE employs, and keep our logic rather simple in terms of how to deal with destroying workspaces.

This application takes advantage of a few different features that TFE provides by default.
 * Checks to see if TFE has the workspace locked.
 * Utilizes the logic of different states the workspace can be in.
 * Makes decisions if a workspace was either applied recently or destroyed.
 * Utilizes the tracking TFE does in terms of plans and applies.
 * Scans through the workspace variables to find workspaces that have the variable set, and utilizes the value to make a determination of what to do next.
 * Utilizes the role based access control with tokens to scope what workspaces are even exposed to this reaper bot.

## Technical Description
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

#### Workspace Settings
For workspaces you wish to destroy, you must set the `Workspace_TTL` with an integer that is counted in hours. This will allow the reaper bot to know how long you intend to keep the workspace around. 

By doing a new apply to the workspace, it will reset the counter time, thus in effect extending the _"lease"_ of the workspace.


# Application Details
## Resource Links
![Image of Resources](https://www.lucidchart.com/publicSegments/view/2275fe76-e2c3-42ec-a737-7de8faea2c31/image.png)

## Decsion Flow
![Decision Flow](https://www.lucidchart.com/publicSegments/view/e5721952-cac3-43d4-9dc1-e9eb5b2410fe/image.png)

## Resources Utilized
 * AWS - Lambda
 * AWS - SQS
 * AWS - DynamoDB
 * AWS - CloudWatch

### Lambda
Two functions are deployed:
 * FindWorkspacesToReap-[orgName]
 * ProcessReaperQueue-[orgName]

 Both functions are in the same Python file (reapWorkspaces.py)

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

