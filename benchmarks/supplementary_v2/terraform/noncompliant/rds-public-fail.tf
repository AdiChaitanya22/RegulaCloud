# Target: CTRL-AWS-RDS-NO-PUBLIC (FAIL)
resource "aws_db_instance" "app_db" {
  instance_class      = "db.t3.micro"
  publicly_accessible = true
  storage_encrypted   = true
}
