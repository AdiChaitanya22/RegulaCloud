resource "aws_ebs_volume" "v" { for_each = toset(["a", "b"])
 encrypted = true }