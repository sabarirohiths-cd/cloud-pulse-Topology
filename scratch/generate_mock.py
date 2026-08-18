import json
import os
import random

def generate_mock():
    # Helper to generate random items
    def gen_list(prefix, count, extra_props=None):
        items = []
        for i in range(1, count + 1):
            item = {"Id": f"{prefix}-{i}", "Name": f"Prod-{prefix.capitalize()}-{i}"}
            if extra_props:
                item.update(extra_props)
            items.append(item)
        return items

    vpcs = []
    
    # 1 Production VPC
    vpc = {
        "VpcId": "vpc-prod-core-001",
        "Name": "Production Core VPC",
        "CidrBlock": "10.0.0.0/16",
        "State": "available",
        "Subnets": [],
        "InternetGateways": [{"Id": "igw-prod-1", "Name": "Prod-IGW"}],
        "RouteTables": gen_list("rtb", 4),
        "NetworkAcls": gen_list("nacl", 2),
        "SecurityGroups": gen_list("sg", 15, {"Description": "Prod security group"}),
        "LoadBalancers": gen_list("alb", 5, {"Type": "application"}),
        "RDSInstances": gen_list("rds", 4, {"Engine": "aurora-postgresql"}),
        "ECSClusters": gen_list("ecs", 2),
        "EKSClusters": gen_list("eks", 1),
        "TransitGatewayAttachments": [{"Id": "tgw-attach-1", "Name": "Prod-TGW-Attach"}],
        "VpnGateways": [{"Id": "vgw-1", "Name": "Prod-VGW"}],
    }

    # Add 12 Subnets
    for i in range(1, 13):
        az = f"ap-south-1{'a' if i%3==1 else 'b' if i%3==2 else 'c'}"
        subnet_type = "Public" if i <= 4 else "Private"
        subnet = {
            "SubnetId": f"subnet-{subnet_type.lower()}-{i}",
            "Name": f"Prod {subnet_type} Subnet {i}",
            "CidrBlock": f"10.0.{i}.0/24",
            "AvailabilityZone": az,
            "State": "available",
            "Instances": gen_list(f"i-prod-{i}", random.randint(2, 6), {"State": "running", "InstanceType": "m5.large"}),
            "AutoScalingGroups": gen_list(f"asg-prod-{i}", random.randint(0, 2)),
            "LambdaFunctions": gen_list(f"lambda-{i}", random.randint(1, 3)),
            "ElastiCacheNodes": gen_list(f"redis-{i}", random.randint(0, 1)),
        }
        if subnet_type == "Public":
            subnet["NatGateways"] = [{"Id": f"nat-{i}", "NatGatewayId": f"nat-{i}", "State": "available"}]
            
        vpc["Subnets"].append(subnet)
        
    vpcs.append(vpc)

    mock_data = {
        "Regions": {
            "ap-south-1": vpcs
        },
        "GlobalResources": {
            "S3Buckets": gen_list("s3-bucket", 15),
            "IAMRoles": gen_list("iam-role", 25),
            "CloudFrontDistributions": gen_list("cloudfront", 3),
            "Route53HostedZones": gen_list("route53", 4)
        }
    }

    output_dir = r"d:\Topology Project\cloud-pulse-Topology\backend\output"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'mock_enterprise_topology.json'), 'w') as f:
        json.dump(mock_data, f, indent=4)

if __name__ == "__main__":
    generate_mock()
    print("Mock topology generated successfully.")
