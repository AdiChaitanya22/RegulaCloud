resource "aws_iam_policy" "p" { policy = jsonencode({
 Statement = [{ Action = "s3:GetObject", Resource = "arn:aws:s3:::myb/*" }]
 }) }