output "webui" {
  value = "${var.ui == true ? "https://${element(concat(aws_s3_bucket.visual_results.*.website_endpoint, list("")), 0)}" : "No Web UI Set"}"
}
