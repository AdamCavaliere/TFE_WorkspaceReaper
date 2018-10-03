output "webui" {
  value = "${var.ui == true ? "https://${element(concat(aws_s3_bucket.visual_results.*.bucket_domain_name, list("")), 0)}/index.html" : "No Web UI Set"}"
}
