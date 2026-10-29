# Semantic Feature: nested_block (PASS)
resource "aws_instance" "server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }
}
