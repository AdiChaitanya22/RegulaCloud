resource "aws_security_group" "sg" { ingress { from_port = 0
 to_port = 65535
 protocol = "tcp"
 ipv6_cidr_blocks = ["::/0"] } }