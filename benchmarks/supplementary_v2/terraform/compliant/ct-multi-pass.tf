# Target: CTRL-AWS-CLOUDTRAIL-MULTI (PASS)
resource "aws_s3_bucket" "trail_bucket" {
  bucket = "corp-audit-cloudtrail-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "trail_bucket_enc" {
  bucket = aws_s3_bucket.trail_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudtrail" "main_audit_trail" {
  name                  = "corp-audit-trail"
  s3_bucket_name        = aws_s3_bucket.trail_bucket.id
  is_multi_region_trail = true
  enable_logging        = true
}
