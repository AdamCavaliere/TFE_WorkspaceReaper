resource "aws_s3_bucket" "visual_results" {
  bucket = "workspacereaper-${var.TFE_ORG}.this-demo.rocks"
  acl    = "public-read"

  website {
    index_document = "index.html"
    error_document = "error.html"
  }
}

resource "aws_s3_bucket_policy" "getitall" {
  bucket = "${aws_s3_bucket.visual_results.id}"

  policy = <<EOF
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Sid":"AddPerm",
      "Effect":"Allow",
      "Principal": "*",
      "Action":["s3:GetObject"],
      "Resource":["${aws_s3_bucket.visual_results.arn}/*"]
    }
  ]
}
EOF
}

locals {
  files    = ["index.html", "css/style.css"]
  root_dir = "functions/static/"
}

resource "aws_s3_bucket_object" "object" {
  count  = "${length(local.files)}"
  bucket = "${aws_s3_bucket.visual_results.id}"
  key    = "${local.files[count.index]}"
  source = "${local.root_dir}${local.files[count.index]}"
  etag   = "${local.root_dir}${local.files[count.index]}"
}
