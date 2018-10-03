output "webui" {
  value = "${var.ui == false ? "No Web UI Set" : "https://${element(concat(aws_s3_bucket.visual_results.*.website_endpoint, list("")), 0)}"}"
}
