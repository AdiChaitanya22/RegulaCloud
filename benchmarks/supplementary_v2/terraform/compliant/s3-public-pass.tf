# Target: CTRL-AWS-S3-NO-PUBLIC (PASS)
resource "aws_s3_bucket" "app_bucket" {
  bucket = "corp-app-isolated-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app_bucket_enc" {
  bucket = aws_s3_bucket.app_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "pab" {
  bucket                  = aws_s3_bucket.app_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
