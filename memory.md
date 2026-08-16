# Topology Pipeline Memory
**Date:** 2026-08-17
**Time:** 01:27:12 (IST)

## Project Summary
We are building a Full-Stack AWS Topology Dashboard utilizing a FastAPI backend and a React Flow frontend. The project has evolved from a simple Python script into a robust, multi-tenant architecture with dynamic database configurations and enterprise-scale service discovery.

## Architecture

### Backend (`FastAPI`)
- **`app.api`**: Contains router endpoints like `/api/v1/topology/scan` to trigger AWS discovery.
- **`app.services.topology_service`**: Manages scanning sessions. It dynamically retrieves the cloud account configuration (`ConfigCloudAccount`) from SQLite, securely decrypts the AWS credentials using `AESGCM`, and spins up the builder.
- **`app.services.aws.topology`**: A highly modularized package utilizing Python Mixins.
  - `networking.py`: VPCs, Subnets, TGW, Route53, Firewalls
  - `compute.py`: EC2, ASG, ECS, EKS, Lambda, SageMaker, Workspaces
  - `database.py`: RDS, ElastiCache, DocumentDB, Redshift
  - `storage.py`: EFS, FSx
  - `messaging.py`: SQS, MQ, MSK, OpenSearch
  - `base.py`: Maintains `boto3` session states, thread pools, and the hierarchical `vpcs` structure.

### Frontend (`React`)
- **React Flow**: Visualizes the topology using `@dagrejs/dagre` for automated Left-to-Right hierarchical rendering.
- **TopologyDetailModal.js**: A dynamic inspection modal that beautifully formats complex JSON metadata (like Security Group rules and ECS tasks) into HTML tables upon clicking nodes.

## Outputs
- The topology engine uses concurrent threads (ThreadPoolExecutor) to build the entire JSON structure rapidly.
- It outputs a unified structure mapping VPCs -> Subnets -> Resources.
- Development output is saved to `backend/output/final_complete_topology.json`.

## AWS Permissions
The application requires comprehensive `Describe` and `List` permissions defined in `policy.txt` to seamlessly enumerate over 20+ different AWS services securely.
