# infrastructure/terraform.tf

# module "shared" {
#   source = "./shared/terraform"
# }

# module "api_server" {
#   source = "./api-server/terraform"
  
#   vpc_id            = module.shared.vpc_id
#   # private_subnets   = module.shared.private_subnets
#   public_subnet_ids = module.shared.public_subnet_ids
#   # api_security_group = module.shared.api_security_group
# }

# # module "bot_platform" {
# #   source = "./bot-platform/terraform"
  
# #   vpc_id            = module.shared.vpc_id
# #   private_subnets   = module.shared.private_subnets
# #   team_names        = var.team_names
# #   api_endpoint      = module.api_server.api_endpoint
# # }