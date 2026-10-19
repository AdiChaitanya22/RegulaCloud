locals { enc = true }
resource "aws_db_instance" "db" { storage_encrypted = local.enc }