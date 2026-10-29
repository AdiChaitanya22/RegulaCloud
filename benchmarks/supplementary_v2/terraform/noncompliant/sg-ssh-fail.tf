# Target: CTRL-AWS-SG-NO-OPEN-SSH (FAIL)
resource "aws_security_group" "bastion_sg" {
  name        = "corp-bastion-sg"
  description = "Unrestricted SSH access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
