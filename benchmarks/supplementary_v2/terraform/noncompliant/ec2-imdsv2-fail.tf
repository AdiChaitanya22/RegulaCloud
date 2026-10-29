# Target: CTRL-AWS-EC2-IMDSV2 (FAIL)
resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  metadata_options {
    http_tokens = "optional"
  }
}
