variable "env" {
  type = string
}

variable "resource_group_name" {
  type = string

}

variable "location" {
  type = string
}

variable "writer_principal_id" {
  type = string
}

variable "tags" {
  type = map(string)
}
