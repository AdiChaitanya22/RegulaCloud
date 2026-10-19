variable "pub" { default = true }
resource "aws_db_instance" "db" { publicly_accessible = var.pub }