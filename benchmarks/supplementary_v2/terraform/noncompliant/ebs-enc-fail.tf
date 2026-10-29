# Target: CTRL-AWS-EBS-ENC (FAIL)
resource "aws_ebs_volume" "database_vol" {
  availability_zone = "us-east-1a"
  size              = 20
  encrypted         = false
}
