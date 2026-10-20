output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  value = aws_instance.app.public_ip
}

output "env_for_toolkit" {
  description = "Put these in the toolkit's .env"
  value       = <<-EOT
    SSH_USERNAME=ec2-user
    SSH_KEY_PATH=${abspath(local_sensitive_file.private_key.filename)}
    AWS_DEFAULT_REGION=${var.region}
  EOT
}

output "ssh_test" {
  value = "ssh -i ${local_sensitive_file.private_key.filename} ec2-user@${aws_instance.app.public_ip}"
}
