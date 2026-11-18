variable "env" {
  type        = string
  description = "Give us the environment we are in dev or prod"
  validation {
    condition     = contains(["dev", "prod", "sbx"], var.env)
    error_message = "environment should be dev, prod or sdbx"
  }
}
