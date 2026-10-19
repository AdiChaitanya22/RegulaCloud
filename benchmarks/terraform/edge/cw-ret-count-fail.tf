resource "aws_cloudwatch_log_group" "lg" { count = 2
 retention_in_days = 14 }