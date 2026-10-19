variable "p" { default = false }
resource "aws_s3_bucket_public_access_block" "pab" { block_public_acls = var.p ? true : false }