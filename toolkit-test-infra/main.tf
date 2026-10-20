terraform {
  required_version = ">= 1.5"
  required_providers {
    aws   = { source = "hashicorp/aws", version = ">= 5.0" }
    tls   = { source = "hashicorp/tls", version = "~> 4.0" }
    local = { source = "hashicorp/local", version = "~> 2.0" }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# ---------- Network: reuse the default VPC (no NAT, no extra cost) ----------
data "aws_vpc" "default" {
  default = true
}

# Only AZs that actually offer the instance type
data "aws_ec2_instance_type_offerings" "available" {
  location_type = "availability-zone"
  filter {
    name   = "instance-type"
    values = [var.instance_type]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
  filter {
    name   = "availability-zone"
    values = data.aws_ec2_instance_type_offerings.available.locations
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ---------- SSH key (generated here, written next to these files) ----------
resource "tls_private_key" "toolkit" {
  algorithm = "ED25519"
}

resource "aws_key_pair" "toolkit" {
  key_name   = "toolkit-test"
  public_key = tls_private_key.toolkit.public_key_openssh
}

resource "local_sensitive_file" "private_key" {
  filename        = "${path.module}/toolkit-test-key.pem"
  content         = tls_private_key.toolkit.private_key_openssh
  file_permission = "0400"
}

# ---------- Security group: SSH from your IP only ----------
resource "aws_security_group" "ssh" {
  name        = "toolkit-test-ssh"
  description = "SSH from my IP only (toolkit test)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- The monitored instance ----------
resource "aws_instance" "app" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.ssh.id]
  key_name                    = aws_key_pair.toolkit.key_name
  associate_public_ip_address = true
  user_data_replace_on_change = true

  metadata_options {
    http_tokens = "required"
  }

  # Seeds /var/log/app.log with one ERROR line for the log check to find
  user_data = <<-EOT
    #!/bin/bash
    cat > /var/log/app.log <<'LOG'
    INFO app started
    INFO order 1001 processed
    ERROR payment failed for order 1002
    LOG
    chmod 644 /var/log/app.log
  EOT

  tags = {
    Name    = "toolkit-test"
    monitor = "true" # the tag the toolkit looks for
  }
}

# ---------- A bucket for the S3 auditor to find ----------
# New buckets are private and encrypted by default, so the expected finding
# is "no lifecycle policy".
resource "aws_s3_bucket" "audit_target" {
  bucket        = "toolkit-test-${data.aws_caller_identity.current.account_id}-${var.region}"
  force_destroy = true
}

resource "aws_s3_object" "sample" {
  bucket  = aws_s3_bucket.audit_target.id
  key     = "sample.txt"
  content = "toolkit test object"
}
