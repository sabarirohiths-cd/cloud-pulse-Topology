class GraphStitcher:
    def __init__(self, regional_data):
        self.regional_data = regional_data
        self.all_vpcs = {}
        for region, vpcs in self.regional_data.items():
            for vpc in vpcs:
                self.all_vpcs[vpc['VpcId']] = vpc

    def stitch(self):
        print("Stitching cross-region connections...")
        for region, vpcs in self.regional_data.items():
            for vpc in vpcs:
                self._validate_peering(vpc)
        return self.regional_data

    def _validate_peering(self, vpc):
        for peer in vpc.get('PeeringConnections', []):
            accepter_id = peer.get('AccepterVpcId')
            if accepter_id and accepter_id not in self.all_vpcs:
                peer['IsExternal'] = True
            else:
                peer['IsExternal'] = False
