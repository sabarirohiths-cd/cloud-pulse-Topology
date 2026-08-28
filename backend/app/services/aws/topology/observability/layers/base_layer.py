from abc import ABC, abstractmethod
from typing import Dict, Any, List

class DiagnosticLayer(ABC):
    """
    Base class for all diagnostic layers.
    """
    
    @property
    @abstractmethod
    def layer_name(self) -> str:
        """Return the name of the layer (e.g., 'infrastructure', 'network_flow', 'application')."""
        pass

    @abstractmethod
    def analyze(self, instance_id: str, fetcher: Any, options: List[str], lookback_minutes: int) -> Dict[str, Any]:
        """
        Run the diagnostic analysis for this layer.
        
        Args:
            instance_id (str): The ID of the EC2 instance being analyzed.
            fetcher (Any): The DiagnosticTracer instance orchestrating the scan (provides access to session, nodes, edges).
            options (List[str]): List of diagnostic options requested (e.g., ['METRICS', 'LOGS', 'XRAY']).
            lookback_minutes (int): Time window in minutes.
            
        Returns:
            Dict[str, Any]: A dictionary containing the verdict and details for this layer.
            Must contain at least 'status' (e.g., 'HEALTHY', 'DEGRADED', 'CRITICAL') and 'summary'.
        """
        pass
