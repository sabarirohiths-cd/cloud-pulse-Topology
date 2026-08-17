# This file now acts as a wrapper for backward compatibility.
# The core logic has been refactored into the `topology` package to handle the massive scaling of services.

from .topology import MultiRegionTopologyBuilder

class AWSTopologyBuilder(MultiRegionTopologyBuilder):
    """
    Wrapper class extending ModularTopologyBuilder.
    All methods, logic, and threading are implemented in backend/app/services/aws/topology/
    """
    pass
