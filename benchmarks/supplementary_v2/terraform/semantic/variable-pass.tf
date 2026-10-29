# Semantic Feature: variable (PASS)
variable "db_public" {
  type    = bool
  default = false
}

resource "aws_db_instance" "db" {
  instance_class      = "db.t3.micro"
  publicly_accessible = var.db_public
  storage_encrypted   = true
}
