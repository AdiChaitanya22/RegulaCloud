# Target: CTRL-AWS-S3-ENC (PASS)
resource "aws_s3_bucket" "data_bucket" {
  bucket = "corp-data-bucket-secure"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket_enc" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
