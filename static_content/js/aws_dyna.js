
AWS.config.update({region: 'us-east-2'});

ddb = new AWS.DynamoDB({apiVersion: '2012-10-08'});
console.log("Hello World")
var savings = {
    TableName: 'WorkspaceReaper-azc',
    Key:{
        'workspaceId': {S:'orgSavings'}
    }
    
};

var workspaces = {
    TableName: 'WorkspaceReaper-azc',
    ExpressionAttributeValues: {
        ":wid" : {
            S: "ws-"
        }
    },
    FilterExpression: "contains (workspaceId, :wid)"
}

ddb.getItem(savings, function(err,data) {
    if (err) {
        console.log("Error", err);
    }
    else {
        console.log("Success", data.Item.destructions)
        var destructions = data.Item.destructions
    }
});

ddb.scan(workspaces, function(err,data) {
    if (err) {
        console.log("Error", err);
    }
    else {
        console.log(data);
        var workspaces = data.Items
    }
});
