import logging
import inspect
from typing import Dict, Any

from .layers.base_layer import DiagnosticLayer
from .layers import InfrastructureLayer, NetworkFlowLayer, ApplicationLayer
from .synthesis_engine import synthesize_root_cause

logger = logging.getLogger(__name__)

class DiagnosticTracer:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.session = fetcher.session
        self.region = fetcher.region
        self.nodes = fetcher.nodes
        self.edges = fetcher.edges
        
        # Dynamically load all imported subclasses of DiagnosticLayer
        self.layers = []
        for name, obj in globals().items():
            if inspect.isclass(obj) and issubclass(obj, DiagnosticLayer) and obj is not DiagnosticLayer:
                self.layers.append(obj())
                
        # Sort layers by priority if needed. We'll just execute them in order they are defined.
        
    def trace(self, instance_id: str, options: list[str], lookback_minutes: int = 15):
        logger.info(f"Running on-demand observability diagnostics for {instance_id}: {options} (lookback: {lookback_minutes}m)")
        
        # CLEAR TERMINAL MESSAGES FOR USER
        print(f"\n{'='*60}")
        print(f"🚀 STARTED DEEP DIAGNOSTICS FOR: {instance_id}")
        print(f"🛠️  Options: {options} | Lookback: {lookback_minutes}m")
        print(f"{'='*60}\n")
        
        options = [opt.upper() for opt in options]
        
        node = next((n for n in self.nodes if n['id'] == instance_id), None)
        if not node:
            logger.warning(f"Node {instance_id} not found in topology graph.")
            print(f"❌ ERROR: Node {instance_id} not found in topology graph.")
            return

        diagnostic_details = {}
        worst_health = "HEALTHY"
        summaries = []

        # Execute each layer
        for layer in self.layers:
            try:
                print(f"   ➔ Executing Diagnostic Layer: {layer.layer_name}...")
                verdict = layer.analyze(instance_id, self, options, lookback_minutes)
                diagnostic_details[layer.layer_name] = verdict
                
                layer_status = verdict.get("status", "UNKNOWN")
                if layer_status == "CRITICAL":
                    worst_health = "CRITICAL"
                elif layer_status == "DEGRADED" and worst_health != "CRITICAL":
                    worst_health = "DEGRADED"
                    
                if verdict.get("summary"):
                    summaries.append(verdict["summary"])
            except Exception as e:
                logger.error(f"Error executing diagnostic layer {layer.layer_name}: {e}")
                print(f"   ❌ ERROR in {layer.layer_name}: {e}")
                diagnostic_details[layer.layer_name] = {
                    "status": "ERROR",
                    "summary": f"Layer crashed: {str(e)}"
                }

        # Run Synthesis Engine
        print(f"   ➔ Executing Automated Synthesis Engine...")
        synthesis_result = synthesize_root_cause(diagnostic_details)
        diagnostic_details['synthesis'] = synthesis_result

        # Update node
        node['health_state'] = worst_health
        node['diagnostic_details'] = diagnostic_details
        
        if summaries:
            # We put a short combined summary here
            node['diagnostic'] = " | ".join(summaries)
        else:
            node['diagnostic'] = "Diagnostics completed with no specific summary."
            
        print(f"\n{'='*60}")
        print(f"✅ FINISHED DEEP DIAGNOSTICS FOR: {instance_id}")
        print(f"🏥 Final Health State: {worst_health}")
        print(f"🧠 Synthesis: {synthesis_result['synthesis_statement']}")
        print(f"{'='*60}\n")
