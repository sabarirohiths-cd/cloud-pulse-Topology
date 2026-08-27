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
