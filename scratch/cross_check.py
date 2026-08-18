import json
import boto3
from collections import Counter
import os

def main():
    json_path = 'd:/Topology Project/cloud-pulse-Topology/backend/output/final_complete_topology.json'
    out_path = 'd:/Topology Project/cloud-pulse-Topology/backend/output/cross_check_results.txt'
    
    with open(json_path, 'r') as f:
        topo = json.load(f)

    json_counts = Counter()
    regions = list(topo.get("Regions", {}).keys())
    print(f"Regions found in JSON: {regions}")

    # 1. Count JSON resources
    for region, vpcs in topo.get("Regions", {}).items():
        for vpc in vpcs:
            for k, v in vpc.items():
                if isinstance(v, list):
                    json_counts[k] += len(v)
            for subnet in vpc.get("Subnets", []):
                for k, v in subnet.items():
                    if isinstance(v, list) and k != "Tags":
                        json_counts[k] += len(v)

    # 2. AWS Resource Tagging API
    aws_counts = Counter()
    for region in regions:
        print(f"Scanning AWS region: {region} via Tagging API...")
        try:
            tag_client = boto3.client('resourcegroupstaggingapi', region_name=region)
            paginator = tag_client.get_paginator('get_resources')
            for page in paginator.paginate():
                for res in page.get('ResourceTagMappingList', []):
                    arn = res['ResourceARN']
                    # arn:aws:rds:us-east-1:123456789012:db:mysql-db
                    parts = arn.split(':')
                    if len(parts) >= 6:
                        service = parts[2]
                        res_type = parts[5].split('/')[0] if '/' in parts[5] else parts[5]
                        aws_counts[f"{service}:{res_type}"] += 1
        except Exception as e2:
            print(f"Failed Tagging API for region {region}: {e2}")

    with open(out_path, 'w') as f:
        f.write("=== RESOURCES FETCHED IN JSON (Topology Builder) ===\n")
        for k, v in sorted(json_counts.items()):
            if v > 0:
                f.write(f"{k}: {v}\n")
                
        f.write("\n=== RESOURCES IN AWS ACCOUNT (via API) ===\n")
        for k, v in aws_counts.most_common():
            f.write(f"{k}: {v}\n")
            
    print(f"Results written to {out_path}")

if __name__ == '__main__':
    main()
