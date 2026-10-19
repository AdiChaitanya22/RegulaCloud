resource "aws_cloudtrail" "ct" { is_multi_region_trail = true
 s3_bucket_name = aws_s3_bucket.b.id }