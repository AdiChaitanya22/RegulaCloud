# Target: CTRL-AWS-KMS-ROTATION (FAIL)
resource "aws_kms_key" "primary_key" {
  description         = "Primary data protection master key"
  enable_key_rotation = false
}
