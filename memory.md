# Topology Pipeline Memory
**Date:** 2026-08-17
**Time:** 01:27:12 (IST)

## Project Summary
We are building a Full-Stack AWS Topology Dashboard utilizing a FastAPI backend and a React Flow frontend. The project has evolved from a simple Python script into a robust, multi-tenant architecture with dynamic database configurations and enterprise-scale service discovery.

## Architecture

### Backend (`FastAPI`)
- **`app.api`**: Contains router endpoints like `/api/v1/topology/scan` to trigger AWS discovery.
- **`app.services.topology_service`**: Manages scanning sessions. It dynamically retrieves the cloud account configuration (`ConfigCloudAccount`) from SQLite, securely decrypts the AWS credentials using `AESGCM`, and spins up the builder.
- **`app.services.aws.topology.tracers`**: A highly modularized package utilizing specific tracer classes inheriting from `base_tracer.py`.
  - `network_tracer.py`: Scans networking components like VPCs, Subnets, and Route Tables.
  - `database_tracer.py`: Scans databases like RDS.
  - `security_tracer.py`: Scans Security Groups and other security configurations.
  - `storage_tracer.py`: Scans storage services like S3, EFS.
  - `iam_tracer.py`: Scans IAM roles and policies.
  - `traffic_tracer.py`: Analyzes traffic routing and load balancers.
  - `base_tracer.py`: Maintains `boto3` session states and base functionality for all tracers.

### Frontend (`React`)
- **React Flow**: Visualizes the topology for automated rendering in `TopologyPage.jsx`.
- **ResourceDetailModal.jsx**: A dynamic inspection modal that formats complex JSON metadata into readable structures upon clicking nodes.
- **ScanConfigurationModal.jsx**: Handles user input for initiating AWS environment scans.

## Outputs
- The topology engine uses concurrent threads (ThreadPoolExecutor) to build the entire JSON structure rapidly.
- It outputs a unified structure mapping VPCs -> Subnets -> Resources.
- Development output is saved to `backend/output/final_complete_topology.json`.

## AWS Permissions
The application requires comprehensive `Describe` and `List` permissions defined in `policy.txt` to seamlessly enumerate over 20+ different AWS services securely.

---

**Date:** 2026-08-28
**Time:** 19:00:00 (IST)

## Recent Accomplishments: Dynamic Runtime Discovery & Observability Integration

1. **Anti-Hardcoding & Agility**: Validated and enforced that the Cloud Pulse Engine uses 100% dynamic discovery. VPC Flow Logs (`network_flow_layer.py`) and Application Logs (`application_layer.py`) dynamically resolve CloudWatch groups and streams via real-time active resource bindings instead of static string matches.
2. **Observability Mapping (`observability_tracer.py`)**: Implemented dynamic extraction of regional CloudWatch Alarms. The tracer parses alarm `Dimensions` to automatically draw `MONITORS` edges linking alarms directly to the targeted compute or database nodes (e.g., EC2, RDS).
3. **Messaging Dependencies (`messaging_tracer.py`)**: Added dynamic discovery of SNS topics, linking CloudWatch alarms to SNS via `TRIGGERS` edges when an `AlarmAction` matches an SNS ARN.
4. **Deep IAM-to-S3 Tracing (`iam_tracer.py`)**: Re-architected IAM mapping to deeply inspect Instance Profiles, Attached Managed Policies, and Inline Policies. It dynamically extracts explicitly granted S3 Bucket ARNs and automatically spins up `S3_BUCKET` nodes linked via `GRANTS_ACCESS_TO` edges, cleanly bypassing global `s3:ListAllMyBuckets` pollution.
5. **Security**: Upgraded `policy.txt` to include essential reading permissions (`sns:ListTopics`, `cloudwatch:DescribeAlarms`, `iam:GetPolicy`, `iam:GetPolicyVersion`, `iam:GetRolePolicy`, `iam:ListRolePolicies`).
