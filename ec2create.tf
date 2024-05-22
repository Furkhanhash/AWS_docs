terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-east-2"
}

resource "aws_instance" "example_server" {
  ami           = "ami-02bf8ce06a8ed6092"
  instance_type = "t2.micro"

  tags = {
    Name = "HashmiExample"
  }
}

output "instance_id" {
  value = aws_instance.example_server.id
}

output "public_ip" {
  value = aws_instance.example_server.public_ip
}
