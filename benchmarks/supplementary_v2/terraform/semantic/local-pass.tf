# Semantic Feature: local (PASS)
locals {
  enable_encryption = true
}

resource "aws_db_instance" "db" {
  instance_class      = "db.t3.micro"
  publicly_accessible = false
  storage_encrypted   = local.enable_encryption
}
