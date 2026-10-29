# Target: CTRL-AWS-SG-NO-OPEN-RDP (FAIL)
resource "aws_security_group" "windows_admin_sg" {
  name        = "corp-windows-admin-sg"
  description = "Unrestricted Windows administration"

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
