# Target: CTRL-AWS-RDS-NO-PUBLIC (PASS)
resource "aws_db_instance" "app_db" {
  instance_class      = "db.t3.micro"
  publicly_accessible = false
  storage_encrypted   = true
}
