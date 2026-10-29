# Semantic Feature: resource_reference (PASS)
resource "aws_s3_bucket" "audit_bucket" {
  bucket = "audit-trail-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_enc" {
  bucket = aws_s3_bucket.audit_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudtrail" "trail" {
  name                  = "audit-trail"
  s3_bucket_name        = aws_s3_bucket.audit_bucket.id
  is_multi_region_trail = true
  enable_logging        = true
}
