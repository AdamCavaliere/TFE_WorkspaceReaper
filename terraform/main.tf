provider "aws" {
  region = "us-east-2"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_lambda_function" "test_lambda" {
  filename         = "../functions/reaper.zip"
  function_name    = "FindWorkspacesToReap"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "reapWorkspaces.findReapableWorkspaces"
  runtime          = "python3.6"

  environment {
    variables = {
      TFE_TOKEN = "${var.TFE_TOKEN}"
      TFE_URL   = "${var.TFE_URL}"
      TFE_ORG   = "${var.TFE_ORG}"
    }
  }
}
