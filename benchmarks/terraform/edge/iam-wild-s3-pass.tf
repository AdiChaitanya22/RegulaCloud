resource "aws_iam_policy" "p" { policy = jsonencode({
 Statement = [{ Action = "s3:*", Resource = "*" }]
 }) }