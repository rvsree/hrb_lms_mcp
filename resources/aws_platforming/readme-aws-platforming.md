# AWS Platforming Guide - HRB LMS MCP Server

**Version:** 1.0  
**Last Updated:** 2026-01-18  
**Target Environment:** AWS ECS Fargate  
**Application:** HRB Leave Management System MCP Server (hrb_lms_mcp)

---

## Table of Contents

1. [Target Architecture](#target-architecture)
2. [Environment/IaC Layout](#environmentiac-layout)
3. [Configuration & Secrets](#configuration--secrets)
4. [Security & Compliance](#security--compliance)
5. [Networking Posture](#networking-posture)
6. [Deployment & CI/CD](#deployment--cicd)
7. [Scaling, Resilience, and DR](#scaling-resilience-and-dr)
8. [Observability & Cost](#observability--cost)

---

## Target Architecture

### AWS Services Used

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Cloud Infrastructure                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐                       │
│  │   CloudFront │──────│  Application │                       │
│  │   (CDN)      │      │  Load Balancer│                      │
│  │   + WAF      │      │  (ALB)        │                       │
│  └──────────────┘      └──────┬───────┘                       │
│                                │                                 │
│                       ┌────────▼────────┐                       │
│                       │  ECS Fargate    │                       │
│                       │  Service        │                       │
│                       │  (hrb_lms_mcp)  │                       │
│                       └────────┬────────┘                       │
│                                │                                 │
│  ┌──────────────┐      ┌──────▼────────┐                       │
│  │   RDS        │      │  ElastiCache  │                       │
│  │  PostgreSQL  │      │  (Redis)      │                       │
│  │  (Leave Data)│      │  (Optional)   │                       │
│  └──────────────┘      └───────────────┘                       │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐                        │
│  │  Secrets     │      │  CloudWatch  │                        │
│  │  Manager     │      │  Logs/Metrics│                        │
│  └──────────────┘      └──────────────┘                        │
│                                                                 │
│  ┌──────────────┐                                              │
│  │  ECR         │                                              │
│  │  (Docker)    │                                              │
│  └──────────────┘                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                ▲
                                │ HTTP/REST (MCP Protocol)
                                │
                    ┌───────────┴───────────┐
                    │  ECS Fargate          │
                    │  (hrb_emp_assist)     │
                    │  (MCP Client)         │
                    └───────────────────────┘
```

### Service Details

1. **ECS Fargate**
   - **Cluster**: `hrb-services-cluster` (shared with hrb_emp_assist)
   - **Service**: `hrb-lms-mcp-service`
   - **Task Definition**: `hrb-lms-mcp`
   - **CPU**: 512 (0.5 vCPU)
   - **Memory**: 1024 MB (1 GB)
   - **Desired Count**: 2 (dev), 2 (staging), 3 (prod)

2. **ECR (Elastic Container Registry)**
   - **Repository**: `hrb-lms-mcp`
   - **Image Scanning**: Enabled on push
   - **Encryption**: AES256

3. **RDS PostgreSQL**
   - **Instance Class**: db.t3.micro (dev), db.t3.small (staging), db.t3.medium (prod)
   - **Engine**: PostgreSQL 15.x
   - **Multi-AZ**: Yes (staging/prod), No (dev)
   - **Backup Retention**: 7 days (dev), 30 days (staging/prod)
   - **Storage**: 20GB (dev), 50GB (staging/prod), auto-scaling enabled

4. **ElastiCache Redis** (Optional)
   - **Purpose**: Query result caching, rate limiting
   - **Node Type**: cache.t3.micro (dev), cache.t3.small (staging/prod)
   - **Multi-AZ**: Yes (staging/prod)

5. **Application Load Balancer (ALB)**
   - **Name**: `hrb-lms-mcp-alb`
   - **Scheme**: Internal (VPC-only) or Internet-facing
   - **Listeners**: HTTP (80), HTTPS (443) with SSL certificate
   - **Target Group**: `hrb-lms-mcp-tg` (port 8080)

6. **CloudWatch**
   - **Log Groups**: `/ecs/hrb-lms-mcp`
   - **Metrics**: ECS container insights, custom application metrics
   - **Alarms**: CPU, memory, error rate, latency

7. **Secrets Manager**
   - **Secrets**: Database credentials, API keys
   - **Rotation**: Quarterly for production secrets

### Networking Components

- **VPC**: `hrb-services-vpc` (shared with hrb_emp_assist)
- **Subnets**: 
  - Public subnets (ALB): 2 AZs
  - Private subnets (ECS, RDS): 2 AZs minimum
- **Internet Gateway**: For public subnet access (if internet-facing ALB)
- **NAT Gateway**: For private subnet egress (2 AZs for HA)
- **Security Groups**:
  - `sg-hrb-lms-mcp-alb`: Allow 80, 443 from VPC CIDR or specific security groups
  - `sg-hrb-lms-mcp-ecs`: Allow from ALB only (port 8080)
  - `sg-hrb-lms-mcp-rds`: Allow from ECS security group (port 5432)

---

## Environment/IaC Layout

### Infrastructure as Code Strategy

**Tool**: Terraform (or AWS CDK)

**Repository Structure**:
```
infrastructure/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── ecs/
│   ├── rds/
│   ├── alb/
│   └── vpc/
└── shared/
    └── common.tf
```

### State Management

- **Backend**: S3 bucket with versioning enabled
- **State File**: `terraform.tfstate` per environment
- **Locking**: DynamoDB table for state locking
- **Workspaces**: Not used (separate directories per environment)

### Resource Tagging Strategy

All resources tagged with:

```hcl
tags = {
  Application     = "hrb-lms-mcp"
  Environment     = "dev|staging|prod"
  Owner           = "development-team"
  CostCenter      = "hr-technology"
  ManagedBy       = "terraform"
  Project         = "hrb-benefits-platform"
  DataClassification = "confidential"
}
```

**Tagging Requirements**:
- **Application**: Identifies the application (`hrb-lms-mcp`)
- **Environment**: Environment identifier (`dev`, `staging`, `prod`)
- **Owner**: Team or individual responsible
- **CostCenter**: For cost allocation
- **ManagedBy**: IaC tool (`terraform`, `cdk`)
- **Project**: Higher-level project grouping
- **DataClassification**: Data sensitivity level (confidential - contains PII)

---

## Configuration & Secrets

### Non-Secret Configuration

**Location**: AWS Systems Manager Parameter Store

**Parameter Paths**:
- `/hrb-lms-mcp/dev/app-config`: Application configuration (JSON)
- `/hrb-lms-mcp/dev/mcp-config`: MCP protocol settings

**Configuration Structure**:
```json
{
  "log_level": "INFO",
  "server_port": 8080,
  "mcp_protocol_version": "1.0",
  "max_concurrent_requests": 100,
  "request_timeout_seconds": 30
}
```

**Update Process**:
1. Update parameter in Parameter Store (via console or CLI)
2. Restart ECS service to pick up changes
3. Or use ECS service update with new task definition

### Secrets Lifecycle

**Secrets Manager Paths**:
- `/hrb-lms-mcp/dev/database`: Database credentials
- `/hrb-lms-mcp/dev/api-key`: API key for authentication

**Secret Structure** (Database Example):
```json
{
  "url": "jdbc:postgresql://rds-endpoint:5432/leave_db",
  "username": "leave_app_user",
  "password": "encrypted-password"
}
```

**Rotation Strategy**:
- **Database Credentials**: Automated rotation every 90 days (RDS managed)
- **API Keys**: Manual rotation quarterly

**Rotation Process**:
1. Create new secret version in Secrets Manager
2. Update ECS task definition to reference new secret version
3. Deploy new task definition (zero-downtime deployment)
4. Verify application functionality
5. Delete old secret version after 7 days

---

## Security & Compliance

### Encryption

**At Rest**:
- **RDS**: Encryption enabled (AES-256), KMS key: `arn:aws:kms:...:key/hr-database`
- **EBS Volumes**: Encryption enabled (ECS task storage)
- **Secrets Manager**: Encrypted with KMS

**In Transit**:
- **ALB → ECS**: TLS 1.2+ (internal VPC)
- **Internet → ALB**: TLS 1.2+ with SSL certificate (ACM)
- **ECS → RDS**: TLS required
- **MCP Client → MCP Server**: TLS 1.2+ (HTTPS)

### KMS Usage

- **Database Encryption Key**: `arn:aws:kms:...:key/hr-database` (shared with hrb_emp_assist)
- **Secrets Manager Key**: `arn:aws:kms:...:key/hr-secrets` (shared)
- **Key Rotation**: Annual rotation enabled
- **Access Control**: IAM policies restrict key usage

### IAM Roles and Least Privilege

**ECS Task Execution Role** (`ecsTaskExecutionRole`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:hrb-lms-mcp/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**ECS Task Role** (`ecsTaskRole`):
- Minimal permissions (no S3 access needed)
- Only CloudWatch metrics if custom metrics are used

**Guardrails**:
- No public RDS instances
- Security groups deny all by default, explicit allow rules only
- IAM policies reviewed quarterly
- CloudTrail enabled for all API calls

### Compliance

- **Data Classification**: Confidential (contains employee PII)
- **Retention**: Per company policy (typically 7 years for HR data)
- **Audit Logging**: CloudTrail, VPC Flow Logs, application logs
- **Access Reviews**: Quarterly IAM access reviews

---

## Networking Posture

### Public vs Private Services

**Public Services** (if internet-facing):
- **ALB**: Internet-facing (if external access needed)
- **CloudFront**: Public CDN endpoints (if used)

**Private Services**:
- **ECS Tasks**: Private subnets, no public IP
- **RDS**: Private subnets, no public access
- **ElastiCache**: Private subnets, no public access

**Recommended**: Internal ALB (VPC-only) for security, unless external access is required.

### Ingress

**Allowed Ingress**:
- **ALB**: From VPC CIDR or specific security groups (hrb_emp_assist ECS security group)
- **ECS**: From ALB security group only (port 8080)
- **RDS**: From ECS security group only (port 5432)

### Egress

**Egress Routes**:
- **ECS → Internet**: Via NAT Gateway (for external API calls, if any)
- **ECS → AWS Services**: Via VPC Endpoints (S3, Secrets Manager, Parameter Store)
- **ECS → hrb_emp_assist**: Via VPC (same VPC) or ALB DNS (if different VPC)

**VPC Endpoints** (for cost optimization):
- **S3**: Gateway endpoint (no cost)
- **Secrets Manager**: Interface endpoint
- **Parameter Store**: Interface endpoint
- **CloudWatch Logs**: Interface endpoint

### NAT Gateway Strategy

- **Dev**: Single NAT Gateway (cost optimization)
- **Staging/Prod**: NAT Gateway per AZ (2 AZs minimum) for HA

---

## Deployment & CI/CD

### ECS Task Definition

**File**: `task-definition.json`

**Key Settings**:
- **CPU**: 512 (0.5 vCPU)
- **Memory**: 1024 MB
- **Network Mode**: `awsvpc`
- **Container Port**: 8080
- **Health Check**: `/actuator/health` endpoint (Spring Boot Actuator)

**Environment Variables** (non-secret):
- `SPRING_PROFILES_ACTIVE`: production
- `LOG_LEVEL`: INFO
- `SERVER_PORT`: 8080

**Secrets** (from Secrets Manager):
- `SPRING_DATASOURCE_URL`: Database connection string
- `SPRING_DATASOURCE_USERNAME`: Database username
- `SPRING_DATASOURCE_PASSWORD`: Database password
- `API_KEY`: API key for authentication (if stored in secrets)

### ECS Service Configuration

**Service Settings**:
- **Desired Count**: 2 (dev), 2 (staging), 3 (prod)
- **Launch Type**: FARGATE
- **Platform Version**: LATEST
- **Health Check Grace Period**: 60 seconds
- **Deployment Configuration**:
  - **Maximum Percent**: 200%
  - **Minimum Healthy Percent**: 100%

### ALB Wiring

**Target Group**:
- **Protocol**: HTTP
- **Port**: 8080
- **Health Check Path**: `/actuator/health`
- **Health Check Interval**: 30 seconds
- **Healthy Threshold**: 2
- **Unhealthy Threshold**: 3
- **Deregistration Delay**: 30 seconds

**Listener Rules**:
- **Default**: Forward to target group
- **Path-based**: `/api/hrb/lms/mcp` → target group

### CI/CD Pipeline (GitHub Actions)

**Workflow File**: `.github/workflows/deploy.yml`

**Pipeline Stages**:
1. **Build**: Build Docker image (Maven build + Docker)
2. **Test**: Run unit and integration tests
3. **Scan**: Security scan (Trivy, Snyk)
4. **Push**: Push to ECR
5. **Deploy**: Update ECS service

**Environment Promotion**:
- **Dev**: Auto-deploy on merge to `develop`
- **Staging**: Auto-deploy on merge to `staging`
- **Prod**: Manual approval required, deploy from `main`

**Deployment Strategy**: Rolling update (ECS default)

### Manual Deployment Steps

```bash
# 1. Build and push Docker image
mvn clean package -DskipTests
docker build -t hrb-lms-mcp:latest .
docker tag hrb-lms-mcp:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hrb-lms-mcp:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hrb-lms-mcp:latest

# 2. Update task definition
aws ecs describe-task-definition --task-definition hrb-lms-mcp --query 'taskDefinition' > task-definition.json
# Edit task-definition.json to update image
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 3. Update service
aws ecs update-service \
  --cluster hrb-services-cluster \
  --service hrb-lms-mcp-service \
  --task-definition hrb-lms-mcp:<new-revision> \
  --force-new-deployment

# 4. Wait for deployment
aws ecs wait services-stable \
  --cluster hrb-services-cluster \
  --services hrb-lms-mcp-service
```

---

## Scaling, Resilience, and DR

### Auto Scaling Policies

**ECS Service Auto Scaling**:
- **Metric**: CPU Utilization
- **Target**: 70% CPU utilization
- **Min Capacity**: 2 (dev), 2 (staging), 3 (prod)
- **Max Capacity**: 10 (dev), 15 (staging), 30 (prod)
- **Scale Out**: Add 1 task when CPU > 70% for 2 minutes
- **Scale In**: Remove 1 task when CPU < 30% for 5 minutes

**Additional Metrics** (optional):
- Memory utilization
- Request count per target
- ALB response time

### Desired Count Strategy

- **Dev**: 2 tasks (cost optimization)
- **Staging**: 2 tasks (testing under load)
- **Prod**: 3 tasks (baseline), auto-scales to 30

### Multi-AZ Configuration

- **ECS Tasks**: Distributed across 2+ AZs
- **RDS**: Multi-AZ enabled (staging/prod)
- **ALB**: Cross-zone load balancing enabled
- **NAT Gateway**: 2 AZs for HA (staging/prod)

### RDS Backups

**Automated Backups**:
- **Retention**: 7 days (dev), 30 days (staging/prod)
- **Backup Window**: 03:00-04:00 UTC (configurable)
- **Snapshot Frequency**: Daily

**Manual Snapshots**:
- Before major deployments
- Before schema changes
- Retention: 90 days

### Restore Procedures

**RDS Point-in-Time Restore**:
1. Identify restore point (timestamp or snapshot)
2. Create new RDS instance from snapshot/PITR
3. Update application configuration to point to new instance
4. Verify data integrity
5. Switch traffic to new instance
6. Decommission old instance

**RTO/RPO Expectations**:
- **RTO (Recovery Time Objective)**: 2 hours (simpler service)
- **RPO (Recovery Point Objective)**: 1 hour (daily backups)

### DR Runbook

**Disaster Scenarios**:
1. **Region Failure**: 
   - Failover to secondary region (if configured)
   - Restore from cross-region backups
   - Update ALB DNS to point to secondary region

2. **RDS Failure**:
   - Promote Multi-AZ standby (automatic)
   - Or restore from snapshot in new AZ

3. **ECS Service Failure**:
   - ECS automatically replaces unhealthy tasks
   - If entire service fails, redeploy from ECR

**DR Testing**: Quarterly DR drills

---

## Observability & Cost

### Required Logs

**CloudWatch Log Groups**:
- `/ecs/hrb-lms-mcp`: Application logs
- `/ecs/hrb-lms-mcp/mcp`: MCP protocol request/response logs
- `/ecs/hrb-lms-mcp/database`: Database query logs (if enabled)

**Log Retention**:
- **Dev**: 7 days
- **Staging**: 14 days
- **Prod**: 30 days

**Log Structure**:
- JSON format for structured logging
- Correlation IDs for request tracing
- Log levels: DEBUG, INFO, WARNING, ERROR

### Metrics

**ECS Container Insights**:
- CPU utilization
- Memory utilization
- Network I/O
- Task count

**Custom Application Metrics**:
- MCP tool call count (per tool)
- MCP tool latency (per tool)
- Database query latency
- Error rate by tool

**ALB Metrics**:
- Request count
- Response time
- HTTP error rates (4xx, 5xx)
- Target health

**RDS Metrics**:
- CPU utilization
- Database connections
- Read/write IOPS
- Storage usage

### Dashboards

**CloudWatch Dashboard**: `hrb-lms-mcp-overview`

**Widgets**:
- ECS service health (task count, CPU, memory)
- MCP tool call rate and latency
- Error rate by tool
- Database connection pool
- Request/response time distribution

### Alerts

**Critical Alarms** (SNS → PagerDuty/Email):
- **Service Unhealthy**: < 50% tasks healthy for 2 minutes
- **High Error Rate**: > 1% error rate for 5 minutes
- **High Latency**: p95 latency > 2s for 5 minutes
- **Database Connection Failure**: Connection errors for 2 minutes

**Warning Alarms** (SNS → Email):
- **High CPU**: > 80% CPU for 10 minutes
- **High Memory**: > 80% memory for 10 minutes
- **Low Task Count**: < desired count for 5 minutes

### Correlation IDs

**Format**: `mcp-{timestamp}-{random}`

**Propagation**:
- Generated at MCP protocol entry point
- Passed via `X-Request-ID` header (if supported)
- Included in all log entries
- Returned in JSON-RPC response (if supported)

### Performance SLOs

**Latency Targets**:
- **Simple Queries** (get_leave_balance): p95 < 500ms
- **Complex Queries** (get_leave_history): p95 < 2 seconds
- **Write Operations** (submit_leave_request): p95 < 1 second

**Error Rate Targets**:
- **Overall Error Rate**: < 0.1%
- **5xx Errors**: < 0.05%
- **Database Errors**: < 0.01%

**Availability Target**: 99.9% uptime

### Cost Optimization

**Right-Sizing**:
- Review CPU/memory usage monthly
- Adjust task definition based on actual usage
- Use Fargate Spot for non-critical workloads (dev/staging)

**Fargate Spot** (Optional):
- **Dev**: 50% Fargate Spot, 50% Fargate (cost savings)
- **Staging**: 30% Fargate Spot, 70% Fargate
- **Prod**: 0% Fargate Spot (reliability priority)

**Cost Levers**:
- **Reserved Capacity**: Not applicable (Fargate)
- **Auto Scaling**: Scale down during off-peak hours
- **VPC Endpoints**: Reduce NAT Gateway data transfer costs
- **Log Retention**: Adjust retention based on compliance needs
- **RDS**: Use smaller instance classes where possible (t3.micro for dev)

**Cost Alerts**:
- Daily cost > $X threshold
- Monthly cost > $Y threshold
- Unusual cost spikes (> 20% increase)

---

## Additional Resources

- **Terraform Modules**: `infrastructure/modules/`
- **Deployment Scripts**: `scripts/deploy/`
- **Runbooks**: `docs/runbooks/`
- **MCP Protocol Spec**: `docs/MCP-PROTOCOL.md`

---

**Last Updated**: 2026-01-18  
**Maintained By**: Platform/DevOps Team  
**Questions**: Contact platform team or create issue
