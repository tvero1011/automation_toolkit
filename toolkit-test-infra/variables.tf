variable "region" {
  type        = string
  default     = "us-east-1"
  description = "Region to deploy in. Must match AWS_DEFAULT_REGION when you run the toolkit."
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP as /32, e.g. 203.0.113.7/32. Find it with: curl https://checkip.amazonaws.com"

  validation {
    condition     = can(cidrhost(var.my_ip_cidr, 0)) && var.my_ip_cidr != "0.0.0.0/0"
    error_message = "Use your own IP in CIDR form (x.x.x.x/32). 0.0.0.0/0 is not allowed."
  }
}

variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "Free-tier eligible on most accounts. t2.micro also works."
}
