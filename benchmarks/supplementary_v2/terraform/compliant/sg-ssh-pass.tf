# Target: CTRL-AWS-SG-NO-OPEN-SSH (PASS)
resource "aws_security_group" "bastion_sg" {
  name        = "corp-bastion-sg"
  description = "Restricted management access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
