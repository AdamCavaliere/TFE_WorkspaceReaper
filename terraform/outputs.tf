output "webui" {
  value = "${aws_s3_bucket_object.rendered_index.website_endpoint}"
}
