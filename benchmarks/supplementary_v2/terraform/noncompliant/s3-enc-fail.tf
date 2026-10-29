# Target: CTRL-AWS-S3-ENC (FAIL)
resource "aws_s3_bucket" "data_bucket" {
  bucket = "corp-data-bucket-unencrypted"
}
