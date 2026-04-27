variable "name" { type = string }
variable "location" { type = string }
variable "image" { type = string }
variable "service_account" { type = string }
variable "container_port" { type = number }
variable "min_instances" { type = number }
variable "max_instances" { type = number }
variable "cpu" { type = string }
variable "memory" { type = string }
variable "cpu_idle" {
  type    = bool
  default = true
}
variable "public_ingress" { type = bool }
variable "plain_env" { type = map(string) }
variable "secret_env" { type = map(string) }
variable "secret_prefix" { type = string }
variable "cloud_sql_instances" {
  type    = list(string)
  default = []
}
