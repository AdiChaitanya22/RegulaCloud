# Semantic Feature: literal (PASS)
resource "aws_ebs_volume" "storage" {
  availability_zone = "us-east-1a"
  size              = 20
  encrypted         = true
}
