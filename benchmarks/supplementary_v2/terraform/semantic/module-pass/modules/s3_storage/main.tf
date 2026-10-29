resource "aws_s3_bucket" "b" {
  bucket = "mod-secure-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "b_enc" {
  bucket = aws_s3_bucket.b.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
