provider "aws" {
  region = "us-east-2"
}

resource "aws_lambda_function" "reaper_lambda" {
  filename         = "../functions/reaper.zip"
  function_name    = "FindWorkspacesToReap-${var.TFE_ORG}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "reapWorkspaces.findReapableWorkspaces"
  source_code_hash = "${base64sha256(file("../functions/reaper.zip"))}"
  runtime          = "python3.6"
  timeout          = 30

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
  filename         = "../functions/reaper.zip"
  function_name    = "ProcessReaperQueue-${var.TFE_ORG}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "reapWorkspaces.processQueue"
  source_code_hash = "${base64sha256(file("../functions/reaper.zip"))}"
  runtime          = "python3.6"
  timeout          = 30

  environment {
    variables = {
      TFE_TOKEN = "${var.TFE_TOKEN}"
      TFE_URL   = "${var.TFE_URL}"
      TFE_ORG   = "${var.TFE_ORG}"
      SQS_QUEUE = "${aws_sqs_queue.reaper_queue.id}"
    }
  }
}

resource "aws_lambda_function" "reaper_ui" {
  filename         = "../functions/reaperui.zip"
  function_name    = "ReaperUIData-${var.TFE_ORG}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "results.pullDetails"
  source_code_hash = "${base64sha256(file("../functions/reaperui.zip"))}"
  runtime          = "python3.6"
  timeout          = 30

  environment {
    variables = {
      TFE_ORG = "${var.TFE_ORG}"
    }
  }
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  batch_size       = 5
  event_source_arn = "${aws_sqs_queue.reaper_queue.arn}"
  enabled          = true
  function_name    = "${aws_lambda_function.process_lambda.arn}"
}

resource "aws_cloudwatch_event_rule" "hourly_run" {
  name                = "TFE_WSR-${var.TFE_ORG}"
  description         = "Check for workspaces to reap hourly"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "daily_running_report" {
  rule      = "${aws_cloudwatch_event_rule.hourly_run.name}"
  target_id = "${aws_lambda_function.reaper_lambda.function_name}"
  arn       = "${aws_lambda_function.reaper_lambda.arn}"
}

resource "aws_lambda_permission" "allow_cloudwatch_instance_usage" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.reaper_lambda.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.hourly_run.arn}"
}
