resource "aws_s3_bucket" "visual_results" {
  bucket = "workspacereaper-${var.TFE_ORG}.this-demo.rocks"
  acl    = "public-read"

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

  website {
    index_document = "index.html"
    error_document = "error.html"
  }
}
