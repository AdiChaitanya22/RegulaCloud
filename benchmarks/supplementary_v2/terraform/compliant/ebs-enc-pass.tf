# Target: CTRL-AWS-EBS-ENC (PASS)
resource "aws_ebs_volume" "database_vol" {
  availability_zone = "us-east-1a"
  size              = 20
  encrypted         = true
}
