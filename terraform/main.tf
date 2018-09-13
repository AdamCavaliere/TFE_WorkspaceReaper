provider "aws" {
  region = "us-east-2"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda-${var.TFE_ORG}"

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

resource "aws_iam_role" "sqs_for_lambda" {
  name = "sqs_for_lambda-${var.TFE_ORG}"

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

resource "aws_iam_role_policy" "read_write_policy" {
  name = "test_policy"
  role = "${aws_iam_role.sqs_for_lambda.id}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "sqs:*"
      ],
      "Effect": "Allow",
      "Resource": "${aws_sqs_queue.reaper_queue.arn}"
    }
  ]
}
EOF
}

resource "aws_lambda_function" "reaper_lambda" {
  filename      = "../functions/reaper.zip"
  function_name = "FindWorkspacesToReap"
  role          = "${aws_iam_role.iam_for_lambda.arn}"
  handler       = "reapWorkspaces.findReapableWorkspaces"
  runtime       = "python3.6"

  environment {
    variables = {
      TFE_TOKEN = "${var.TFE_TOKEN}"
      TFE_URL   = "${var.TFE_URL}"
      TFE_ORG   = "${var.TFE_ORG}"
      SQS_QUEUE = "${aws_sqs_queue.reaper_queue.id}"
    }
  }
}

resource "aws_lambda_function" "process_lambda" {
  filename      = "../functions/reaper.zip"
  function_name = "ProcessReaperQueue"
  role          = "${aws_iam_role.sqs_for_lambda.arn}"
  handler       = "reapWorkspaces.processQueue"
  runtime       = "python3.6"

  environment {
    variables = {
      TFE_TOKEN = "${var.TFE_TOKEN}"
      TFE_URL   = "${var.TFE_URL}"
      TFE_ORG   = "${var.TFE_ORG}"
      SQS_QUEUE = "${aws_sqs_queue.reaper_queue.id}"
    }
  }
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  batch_size       = 10
  event_source_arn = "${aws_sqs_queue.reaper_queue.arn}"
  enabled          = true
  function_name    = "${aws_lambda_function.process_lambda.arn}"
}
