output "webui" {
  value = "${aws_s3_bucket_object.object.website_endpoint}"
}
