resource "aws_s3_bucket" "b" {}
resource "aws_s3_bucket_server_side_encryption_configuration" "e" { bucket = aws_s3_bucket.b.id
 rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } } }