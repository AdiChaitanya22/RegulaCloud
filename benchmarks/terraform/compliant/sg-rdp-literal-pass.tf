resource "aws_security_group" "sg" { ingress { from_port = 3389
 to_port = 3389
 protocol = "tcp"
 cidr_blocks = ["10.0.0.0/8"] } }