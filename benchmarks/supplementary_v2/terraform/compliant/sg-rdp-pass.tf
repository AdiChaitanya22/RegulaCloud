# Target: CTRL-AWS-SG-NO-OPEN-RDP (PASS)
resource "aws_security_group" "windows_admin_sg" {
  name        = "corp-windows-admin-sg"
  description = "Restricted Windows administration"

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
