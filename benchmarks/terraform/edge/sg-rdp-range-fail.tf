resource "aws_security_group" "sg" { ingress { from_port = 3000
 to_port = 4000
 protocol = "tcp"
 cidr_blocks = ["0.0.0.0/0"] } }