output "webui" {
  value = "${aws_s3_bucket.visual_results.website_endpoint}"
}
