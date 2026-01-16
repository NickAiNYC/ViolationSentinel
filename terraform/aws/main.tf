# AWS Infrastructure with Terraform
# EKS, RDS, ElastiCache, S3, CloudFront

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "violationsentinel-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "violationsentinel-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "ViolationSentinel"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# VPC Configuration
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "violationsentinel-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = false
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {
    Name = "violationsentinel-vpc"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "violationsentinel-${var.environment}"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true
  
  eks_managed_node_groups = {
    application = {
      min_size     = 3
      max_size     = 20
      desired_size = 5

      instance_types = ["t3.xlarge"]
      capacity_type  = "ON_DEMAND"
      
      labels = {
        role = "application"
      }
    }
    
    workers = {
      min_size     = 2
      max_size     = 10
      desired_size = 5

      instance_types = ["t3.large"]
      capacity_type  = "SPOT"
      
      labels = {
        role = "worker"
      }
    }
  }

  tags = {
    Name = "violationsentinel-eks"
  }
}

# RDS PostgreSQL with TimescaleDB
resource "aws_db_instance" "postgres" {
  identifier     = "violationsentinel-db"
  engine         = "postgres"
  engine_version = "14.9"
  instance_class = "db.r6g.2xlarge"

  allocated_storage     = 500
  max_allocated_storage = 2000
  storage_type         = "gp3"
  storage_encrypted    = true

  db_name  = "violationsentinel"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  multi_az               = true
  deletion_protection    = true
  skip_final_snapshot   = false
  final_snapshot_identifier = "violationsentinel-final-snapshot"

  performance_insights_enabled = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Name = "violationsentinel-db"
  }
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "violationsentinel-redis"
  replication_group_description = "Redis cluster for ViolationSentinel"

  engine               = "redis"
  engine_version       = "7.0"
  node_type           = "cache.r6g.large"
  num_cache_clusters  = 3
  port                = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  automatic_failover_enabled = true
  multi_az_enabled          = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"

  tags = {
    Name = "violationsentinel-redis"
  }
}

# S3 Bucket for Reports and Assets
resource "aws_s3_bucket" "reports" {
  bucket = "violationsentinel-reports-${var.environment}"

  tags = {
    Name = "violationsentinel-reports"
  }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled    = true
  comment            = "ViolationSentinel CDN"
  default_root_object = "index.html"
  price_class        = "PriceClass_100"

  origin {
    domain_name = aws_s3_bucket.reports.bucket_regional_domain_name
    origin_id   = "S3-Reports"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-Reports"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "violationsentinel-cdn"
  }
}

# Security Groups
resource "aws_security_group" "rds" {
  name        = "violationsentinel-rds-sg"
  description = "Security group for RDS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "redis" {
  name        = "violationsentinel-redis-sg"
  description = "Security group for Redis"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Subnet Groups
resource "aws_db_subnet_group" "main" {
  name       = "violationsentinel-db-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Name = "violationsentinel-db-subnet"
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "violationsentinel-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_cloudfront_origin_access_identity" "main" {
  comment = "ViolationSentinel OAI"
}

# Outputs
output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.main.domain_name
}
