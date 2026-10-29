# Semantic Feature: for_each (PASS)
resource "aws_ebs_volume" "vols" {
  for_each          = toset(["app-vol-1", "app-vol-2", "app-vol-3"])
  availability_zone = "us-east-1a"
  size              = 20
  encrypted         = true
}
