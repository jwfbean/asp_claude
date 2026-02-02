#!/usr/bin/env python3
"""
Shared Atlas Stream Processing API library
Common functionality for connection and processor management
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPDigestAuth


def colorize_json(obj):
    """Add color codes to JSON output for terminal display"""
    import json
    
    def colorize_value(value, indent=0):
        spaces = "  " * indent
        if isinstance(value, dict):
            if not value:
                return "{}"
            items = []
            for k, v in value.items():
                colored_key = f'\033[94m"{k}"\033[0m'  # Blue for keys
                colored_value = colorize_value(v, indent + 1)
                items.append(f"{spaces}  {colored_key}: {colored_value}")
            return "{\n" + ",\n".join(items) + f"\n{spaces}}}"
        elif isinstance(value, list):
            if not value:
                return "[]"
            items = []
            for item in value:
                colored_item = colorize_value(item, indent + 1)
                items.append(f"{spaces}  {colored_item}")
            return "[\n" + ",\n".join(items) + f"\n{spaces}]"
        elif isinstance(value, str):
            return f'\033[92m"{value}"\033[0m'  # Green for strings
        elif isinstance(value, (int, float)):
            return f'\033[93m{value}\033[0m'  # Yellow for numbers
        elif isinstance(value, bool):
            return f'\033[95m{str(value).lower()}\033[0m'  # Magenta for booleans
        elif value is None:
            return f'\033[90mnull\033[0m'  # Gray for null
        else:
            return str(value)
    
    return colorize_value(obj)


class AtlasStreamProcessingAPI:
    """Atlas Stream Processing API client with common operations"""
    
    def __init__(self, config_file: str = "../config.txt"):
        self.config = self._load_config(config_file)
        self.auth = HTTPDigestAuth(
            self.config["PUBLIC_KEY"], 
            self.config["PRIVATE_KEY"]
        )
        self.project_url = f"https://cloud.mongodb.com/api/atlas/v2/groups/{self.config['PROJECT_ID']}"
        
        # Stream Processing Workspace configuration
        if self.config.get('SP_WORKSPACE_NAME'):
            # Primary workspace-based API
            self.base_url = f"{self.project_url}/streams/{self.config['SP_WORKSPACE_NAME']}"
            self.api_model = "workspace"
        elif self.config.get('SP_INSTANCE_NAME'):
            # Backward compatibility - treat instances as workspaces
            self.base_url = f"{self.project_url}/streams/{self.config['SP_INSTANCE_NAME']}"
            self.api_model = "workspace"
        else:
            self.base_url = None
            self.api_model = None
            
        self.headers = {"Accept": "application/vnd.atlas.2024-05-30+json"}
        # Use newer API version for tier support
        self.headers_v2025 = {"Accept": "application/vnd.atlas.2025-03-12+json"}
    
    def _load_config(self, config_file: str) -> Dict[str, str]:
        """Load configuration from api.txt file"""
        config = {}
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file {config_file} not found")
        
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
        
        required_keys = ["PUBLIC_KEY", "PRIVATE_KEY", "PROJECT_ID"]
        # SP_INSTANCE_NAME is now optional - required only for processor/connection operations
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")
        
        return config
    
    def analyze_processor_complexity(self, processor_name: str) -> str:
        """Analyze processor complexity and recommend optimal tier"""
        analysis = self.analyze_processor_complexity_detailed(processor_name)
        return analysis["recommended_tier"]
    
    def analyze_processor_complexity_detailed(self, processor_name: str) -> dict:
        """Analyze processor complexity and return detailed analysis"""
        try:
            processor_data = None
            
            # First try to get from local file
            processors_dir = Path("../../processors")
            processor_file = processors_dir / f"{processor_name}.json"
            
            if processor_file.exists():
                with open(processor_file, 'r') as f:
                    processor_data = json.load(f)
            else:
                # Fallback: get processor definition from Atlas API
                try:
                    response = requests.get(
                        f"{self.base_url}/processor/{processor_name}",
                        auth=self.auth,
                        headers=self.headers
                    )
                    if response.status_code == 200:
                        processor_data = response.json()
                except:
                    pass
            
            if not processor_data:
                return {
                    "recommended_tier": "SP10",
                    "analysis": {"error": "Processor not found locally or in Atlas"},
                    "reasoning": "Default fallback for missing processor"
                }
            
            pipeline = processor_data.get("pipeline", [])
            complexity_score = 0
            connections_count = 0
            total_parallelism = 0
            complexity_factors = []
            parallelism_details = []
            
            # Analyze pipeline complexity
            for i, stage in enumerate(pipeline):
                stage_name = f"Stage {i+1}"
                
                # Complex operations
                if "$function" in str(stage):
                    complexity_score += 40
                    complexity_factors.append(f"{stage_name}: JavaScript function (+40 complexity)")
                if "$window" in str(stage):
                    complexity_score += 30
                    complexity_factors.append(f"{stage_name}: Window processing (+30 complexity)")
                if "$facet" in str(stage):
                    complexity_score += 25
                    complexity_factors.append(f"{stage_name}: Facet operation (+25 complexity)")
                if "$lookup" in str(stage):
                    complexity_score += 20
                    complexity_factors.append(f"{stage_name}: Lookup/join operation (+20 complexity)")
                if "$group" in str(stage):
                    complexity_score += 15
                    complexity_factors.append(f"{stage_name}: Grouping operation (+15 complexity)")
                if "$sort" in str(stage):
                    complexity_score += 10
                    complexity_factors.append(f"{stage_name}: Sort operation (+10 complexity)")
                
                # Count connections (sources and sinks)
                if "$source" in stage:
                    connections_count += 1
                if "$merge" in stage:
                    connections_count += 1
                
                # Extract parallelism settings - only count parallelism > 1
                # Check at multiple levels: stage level, operator config level, and nested
                if isinstance(stage, dict):
                    for key, value in stage.items():
                        # Direct parallelism at stage level
                        if key == "parallelism" and isinstance(value, (int, float)):
                            parallelism_val = int(value)
                            if parallelism_val > 1:
                                contribution = parallelism_val - 1
                                total_parallelism += contribution
                                parallelism_details.append(f"{stage_name} ({list(stage.keys())[0]}): parallelism={parallelism_val} (contributes {contribution})")
                                complexity_score += parallelism_val * 5
                        # Parallelism inside operator config (e.g., $merge.parallelism)
                        elif isinstance(value, dict):
                            if "parallelism" in value:
                                parallel_val = value.get("parallelism", 1)
                                if isinstance(parallel_val, (int, float)):
                                    parallelism_val = int(parallel_val)
                                    if parallelism_val > 1:
                                        contribution = parallelism_val - 1
                                        total_parallelism += contribution
                                        parallelism_details.append(f"{stage_name} ({key}): parallelism={parallelism_val} (contributes {contribution})")
                                        complexity_score += parallelism_val * 5
                            # Also check nested "into" for $merge
                            if "into" in value and isinstance(value.get("into"), dict):
                                into_config = value["into"]
                                if "parallelism" in into_config:
                                    parallel_val = into_config.get("parallelism", 1)
                                    if isinstance(parallel_val, (int, float)):
                                        parallelism_val = int(parallel_val)
                                        if parallelism_val > 1:
                                            contribution = parallelism_val - 1
                                            total_parallelism += contribution
                                            parallelism_details.append(f"{stage_name} ({key}.into): parallelism={parallelism_val} (contributes {contribution})")
                                            complexity_score += parallelism_val * 5
                
                # Check for Kafka partitions
                if "kafka" in str(stage).lower():
                    complexity_score += 15
                    complexity_factors.append(f"{stage_name}: Kafka integration (+15 complexity)")
            
            # Pipeline length factor
            pipeline_length = len(pipeline)
            if pipeline_length > 8:
                complexity_score += 20
                complexity_factors.append(f"Pipeline length: {pipeline_length} stages (+20 complexity)")
            elif pipeline_length > 5:
                complexity_score += 10
                complexity_factors.append(f"Pipeline length: {pipeline_length} stages (+10 complexity)")
            elif pipeline_length > 3:
                complexity_score += 5
                complexity_factors.append(f"Pipeline length: {pipeline_length} stages (+5 complexity)")
            
            # Connection count factor
            if connections_count > 4:
                complexity_score += 15
                complexity_factors.append(f"Connection count: {connections_count} (+15 complexity)")
            elif connections_count > 2:
                complexity_score += 10
                complexity_factors.append(f"Connection count: {connections_count} (+10 complexity)")
            
            # Apply parallelism-based tier minimums
            if total_parallelism > 48:
                min_tier_from_parallelism = "SP50"
            elif total_parallelism > 8:
                min_tier_from_parallelism = "SP30"
            elif total_parallelism > 1:
                min_tier_from_parallelism = "SP10"
            elif total_parallelism == 1:
                min_tier_from_parallelism = "SP5"
            else:
                min_tier_from_parallelism = "SP2"
            
            # Determine tier based on complexity score
            if complexity_score >= 80:
                recommended_tier = "SP50"
                complexity_reason = "Very complex pipeline (80+ complexity points)"
            elif complexity_score >= 50:
                recommended_tier = "SP30"
                complexity_reason = "Complex pipeline (50+ complexity points)"
            elif complexity_score >= 25:
                recommended_tier = "SP10"
                complexity_reason = "Moderate complexity (25+ complexity points)"
            elif complexity_score >= 10:
                recommended_tier = "SP5"
                complexity_reason = "Simple pipeline (10+ complexity points)"
            else:
                recommended_tier = "SP2"
                complexity_reason = "Very simple pipeline (<10 complexity points)"
            
            # Use the higher of complexity-based recommendation or parallelism minimum
            tier_hierarchy = ["SP2", "SP5", "SP10", "SP30", "SP50"]
            complexity_index = tier_hierarchy.index(recommended_tier)
            parallelism_index = tier_hierarchy.index(min_tier_from_parallelism)
            
            final_tier = tier_hierarchy[max(complexity_index, parallelism_index)]
            
            # Build reasoning
            if complexity_index >= parallelism_index:
                primary_reason = f"Complexity-driven: {complexity_reason}"
                secondary_reason = f"Parallelism requirement: {min_tier_from_parallelism} (total parallelism: {total_parallelism})"
            else:
                primary_reason = f"Parallelism-driven: {min_tier_from_parallelism} required for {total_parallelism} total parallelism"
                secondary_reason = f"Complexity score: {complexity_score} (suggests {recommended_tier})"
            
            return {
                "recommended_tier": final_tier,
                "analysis": {
                    "total_parallelism": total_parallelism,
                    "complexity_score": complexity_score,
                    "pipeline_stages": pipeline_length,
                    "connections_count": connections_count,
                    "complexity_tier": recommended_tier,
                    "parallelism_tier": min_tier_from_parallelism,
                    "parallelism_details": parallelism_details,
                    "complexity_factors": complexity_factors
                },
                "reasoning": {
                    "primary": primary_reason,
                    "secondary": secondary_reason,
                    "final_decision": f"Selected {final_tier} as the higher requirement"
                }
            }
                
        except Exception as e:
            return {
                "recommended_tier": "SP10",
                "analysis": {"error": str(e)},
                "reasoning": "Error occurred during analysis, using default tier"
            }
    
    def _parse_tier_validation_error(self, error_text: str) -> str:
        """Parse API validation errors to extract minimum tier requirement"""
        try:
            # Look for pattern: "Minimum tier for this workload: SP10 or larger"
            import re
            match = re.search(r'Minimum tier for this workload: (SP\d+)', error_text)
            if match:
                return match.group(1)
            
            # Look for parallelism limit patterns
            parallelism_match = re.search(r'Requested: (\d+)', error_text)
            if parallelism_match:
                requested_parallelism = int(parallelism_match.group(1))
                if requested_parallelism > 8:
                    return "SP50"
                elif requested_parallelism > 4:
                    return "SP30"
                elif requested_parallelism > 2:
                    return "SP10"
                else:
                    return "SP5"
        except:
            pass
        return None
    
    def _substitute_variables(self, text: str) -> str:
        """Substitute ${VAR} placeholders with config values"""
        def replace_var(match):
            var_name = match.group(1)
            return self.config.get(var_name, match.group(0))
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, text)
    
    # Stream Processing Instance Operations
    def list_instances(self) -> List[Dict]:
        """Get list of all Stream Processing instances in the project"""
        try:
            response = requests.get(
                f"{self.project_url}/streams",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {
                "operation": "list_instances",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }
    
    def create_instance(self, instance_name: str, cloud_provider: str = "AWS", region: str = "US_EAST_1") -> Dict:
        """Create a new Stream Processing instance"""
        try:
            payload = {
                "name": instance_name,
                "dataProcessRegion": {
                    "cloudProvider": cloud_provider,
                    "region": region
                }
            }
            response = requests.post(
                f"{self.project_url}/streams",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return {
                "name": instance_name,
                "operation": "create_instance",
                "status": "created",
                "message": "Stream Processing instance created successfully",
                "cloud_provider": cloud_provider,
                "region": region
            }
            
        except requests.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 409:
                return {
                    "name": instance_name,
                    "operation": "create_instance",
                    "status": "already_exists", 
                    "message": "Stream Processing instance already exists"
                }
            return {
                "name": instance_name,
                "operation": "create_instance",
                "status": "failed",
                "message": str(e),
                "http_code": status_code
            }
    
    def delete_instance(self, instance_name: str) -> Dict:
        """Delete a Stream Processing instance"""
        try:
            response = requests.delete(
                f"{self.project_url}/streams/{instance_name}",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            
            return {
                "name": instance_name,
                "operation": "delete_instance",
                "status": "deleted",
                "message": "Stream Processing instance deleted successfully"
            }
            
        except requests.RequestException as e:
            return {
                "name": instance_name,
                "operation": "delete_instance",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }
    
    def get_instance_details(self, instance_name: str) -> Dict:
        """Get details of a specific Stream Processing instance"""
        try:
            response = requests.get(
                f"{self.project_url}/streams/{instance_name}",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            return {
                "name": instance_name,
                "operation": "get_instance_details",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }
    
    def _check_workspace_required(self):
        """Check if workspace name is configured and base_url is available"""
        if not self.base_url:
            raise ValueError("Stream Processing workspace not configured. Please set SP_WORKSPACE_NAME or SP_INSTANCE_NAME in config.txt.")
    
    def _get_detailed_error(self, e):
        """Get detailed error message from API response"""
        error_detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_body = e.response.json()
                error_detail = f"{str(e)} - {error_body.get('detail', error_body)}"
            except:
                error_detail = f"{str(e)} - {e.response.text}"
        return error_detail
    
    # Processor Operations
    def list_processors(self, verbose: bool = False) -> List[Dict]:
        """Get list of all processors with tier information"""
        self._check_workspace_required()
        response = requests.get(
            f"{self.base_url}/processors",
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()
        processors = response.json().get("results", [])
        
        # Enhance each processor with tier information if available
        enhanced_processors = []
        for processor in processors:
            # Try to get detailed processor info including tier
            try:
                # Build URL with verbose parameter if needed
                detail_url = f"{self.base_url}/processor/{processor['name']}"
                params = {}
                if verbose:
                    # Try different parameter formats that Atlas API might expect
                    params = {
                        'includeCount': 'true',  # Common Atlas API pattern
                        'verbose': 'true',       # Direct verbose flag
                        'options.verbose': 'true'  # Nested options pattern
                    }
                
                detail_response = requests.get(
                    detail_url,
                    auth=self.auth,
                    headers=self.headers,
                    params=params if params else None
                )
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    processor["tier"] = detail_data.get("tier", "unknown")
                    processor["scaleFactor"] = detail_data.get("scaleFactor", "unknown")
                    
                    # Add verbose stats if available
                    if "stats" in detail_data:
                        processor["stats"] = detail_data["stats"]
                    
                    # Add errorMsg if present (for failed processors)
                    if "errorMsg" in detail_data:
                        processor["errorMsg"] = detail_data["errorMsg"]
                    
                    # Add all available data when verbose
                    if verbose:
                        # Merge all detail data into processor
                        for key, value in detail_data.items():
                            if key not in processor:  # Don't overwrite existing keys
                                processor[key] = value
                else:
                    processor["tier"] = "unknown"
                    processor["scaleFactor"] = "unknown"
            except:
                processor["tier"] = "unknown" 
                processor["scaleFactor"] = "unknown"
                
            enhanced_processors.append(processor)
        
        return enhanced_processors
    
    def get_processor_status(self) -> Dict:
        """Get status of all processors"""
        timestamp = datetime.now(timezone.utc).isoformat()
        result = {
            "timestamp": timestamp,
            "operation": "status",
            "summary": {"total": 0, "success": 0, "failed": 0},
            "processors": []
        }
        
        try:
            processors = self.list_processors()
            result["summary"]["total"] = len(processors)
            
            for processor in processors:
                proc_info = {
                    "name": processor["name"],
                    "operation": "status",
                    "status": processor.get("state", "UNKNOWN"),
                    "message": "Status retrieved successfully"
                }
                result["processors"].append(proc_info)
                result["summary"]["success"] += 1
                
        except requests.RequestException as e:
            result["summary"]["failed"] = 1
            result["processors"].append({
                "name": "API_ERROR",
                "operation": "status",
                "status": "ERROR",
                "message": str(e)
            })
        
        return result
    
    def get_processor_stats(self, verbose: bool = False) -> Dict:
        """Get detailed stats of all processors"""
        timestamp = datetime.now(timezone.utc).isoformat()
        result = {
            "timestamp": timestamp,
            "operation": "stats",
            "summary": {"total": 0, "success": 0, "failed": 0},
            "processors": []
        }
        
        try:
            processors = self.list_processors(verbose=verbose)
            result["summary"]["total"] = len(processors)
            
            for processor in processors:
                stats = processor.get("stats", {})
                proc_info = {
                    "name": processor["name"],
                    "operation": "stats",
                    "status": processor.get("state", "UNKNOWN"),
                    "message": "Stats retrieved successfully",
                }
                
                if verbose and "full_response" in processor:
                    # Use the complete stats from the API response
                    api_stats = processor["full_response"].get("stats", {})
                    proc_info["stats"] = api_stats
                    # Also include pipeline info if verbose
                    if "pipeline" in processor["full_response"]:
                        proc_info["pipeline"] = processor["full_response"]["pipeline"]
                else:
                    # Use the limited stats subset for regular output
                    proc_info["stats"] = {
                        "processor": processor["name"],
                        "state": processor.get("state", "UNKNOWN"),
                        "inputMessageCount": stats.get("inputMessageCount", 0),
                        "outputMessageCount": stats.get("outputMessageCount", 0),
                        "dlqMessageCount": stats.get("dlqMessageCount", 0),
                        "memoryUsageBytes": stats.get("memoryUsageBytes", 0),
                        "lastMessageIn": stats.get("lastMessageIn"),
                        "scaleFactor": stats.get("scaleFactor", 1)
                    }
                result["processors"].append(proc_info)
                result["summary"]["success"] += 1
                
        except requests.RequestException as e:
            result["summary"]["failed"] = 1
            result["processors"].append({
                "name": "API_ERROR",
                "operation": "stats",
                "status": "ERROR",
                "message": str(e)
            })
        
        return result
    
    def get_single_processor_status(self, processor_name: str) -> Dict:
        """Get status of a specific processor"""
        timestamp = datetime.now(timezone.utc).isoformat()
        result = {
            "timestamp": timestamp,
            "operation": "status",
            "summary": {"total": 1, "success": 0, "failed": 0},
            "processors": []
        }
        
        try:
            processors = self.list_processors()
            target_processor = None
            
            for processor in processors:
                if processor["name"] == processor_name:
                    target_processor = processor
                    break
            
            if target_processor:
                proc_info = {
                    "name": processor_name,
                    "operation": "status",
                    "status": target_processor.get("state", "UNKNOWN"),
                    "message": "Status retrieved successfully"
                }
                result["processors"].append(proc_info)
                result["summary"]["success"] = 1
            else:
                result["processors"].append({
                    "name": processor_name,
                    "operation": "status",
                    "status": "NOT_FOUND",
                    "message": f"Processor '{processor_name}' not found"
                })
                result["summary"]["failed"] = 1
                
        except requests.RequestException as e:
            result["summary"]["failed"] = 1
            result["processors"].append({
                "name": processor_name,
                "operation": "status",
                "status": "ERROR",
                "message": str(e)
            })
        
        return result
    
    def get_single_processor_stats(self, processor_name: str, verbose: bool = False) -> Dict:
        """Get detailed stats of a specific processor"""
        timestamp = datetime.now(timezone.utc).isoformat()
        result = {
            "timestamp": timestamp,
            "operation": "stats",
            "summary": {"total": 1, "success": 0, "failed": 0},
            "processors": []
        }
        
        try:
            processors = self.list_processors(verbose=verbose)
            target_processor = None
            
            for processor in processors:
                if processor["name"] == processor_name:
                    target_processor = processor
                    break
            
            if target_processor:
                stats = target_processor.get("stats", {})
                proc_info = {
                    "name": processor_name,
                    "operation": "stats",
                    "status": target_processor.get("state", "UNKNOWN"),
                    "message": "Stats retrieved successfully",
                }
                
                if verbose and "full_response" in target_processor:
                    # Use the complete stats from the API response
                    api_stats = target_processor["full_response"].get("stats", {})
                    proc_info["stats"] = api_stats
                    # Also include pipeline info if verbose
                    if "pipeline" in target_processor["full_response"]:
                        proc_info["pipeline"] = target_processor["full_response"]["pipeline"]
                else:
                    # Use the limited stats subset for regular output
                    proc_info["stats"] = {
                        "processor": processor_name,
                        "state": target_processor.get("state", "UNKNOWN"),
                        "inputMessageCount": stats.get("inputMessageCount", 0),
                        "outputMessageCount": stats.get("outputMessageCount", 0),
                        "dlqMessageCount": stats.get("dlqMessageCount", 0),
                        "memoryUsageBytes": stats.get("memoryUsageBytes", 0),
                        "lastMessageIn": stats.get("lastMessageIn"),
                        "scaleFactor": stats.get("scaleFactor", 1)
                    }
                result["processors"].append(proc_info)
                result["summary"]["success"] = 1
            else:
                result["processors"].append({
                    "name": processor_name,
                    "operation": "stats",
                    "status": "NOT_FOUND",
                    "message": f"Processor '{processor_name}' not found"
                })
                result["summary"]["failed"] = 1
                
        except requests.RequestException as e:
            result["summary"]["failed"] = 1
            result["processors"].append({
                "name": processor_name,
                "operation": "stats",
                "status": "ERROR",
                "message": str(e)
            })
        
        return result
    
    def sample_processor(self, processor_name: str, num_samples: int = 3) -> Dict:
        """Sample output from a processor by reading from its target collection"""
        result = {
            "processor": processor_name,
            "operation": "schema",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "samples": [],
            "count": 0
        }
        
        try:
            # Get processor details to find its merge target
            proc_stats = self.get_single_processor_stats(processor_name, verbose=True)
            
            if not proc_stats or "processors" not in proc_stats or not proc_stats["processors"]:
                result["status"] = "failed"
                result["message"] = f"Processor {processor_name} not found"
                return result
            
            proc_data = proc_stats["processors"][0]
            pipeline = proc_data.get("pipeline", [])
            
            # Find the $merge stage to get the target collection
            target_db = None
            target_coll = None
            
            for stage in pipeline:
                if "$merge" in stage:
                    merge_into = stage["$merge"].get("into", {})
                    target_db = merge_into.get("db")
                    target_coll = merge_into.get("coll")
                    break
            
            if not target_db or not target_coll:
                result["status"] = "failed"
                result["message"] = f"No $merge stage found in processor {processor_name} pipeline"
                return result
            
            # Read sample documents from the target collection
            from pymongo import MongoClient
            
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                result["status"] = "failed"
                result["message"] = "TARGET_URL not found in config"
                return result
            
            target_url = target_url.strip('"')
            client = MongoClient(target_url)
            db = client[target_db]
            collection = db[target_coll]
            
            # Get sample documents
            samples = list(collection.find().limit(num_samples))
            
            # Convert ObjectIds to strings for JSON serialization
            for doc in samples:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            client.close()
            
            result["samples"] = samples
            result["count"] = len(samples)
            result["target_collection"] = f"{target_db}.{target_coll}"
            result["status"] = "success"
            result["message"] = f"Retrieved {len(samples)} sample document(s) from {target_db}.{target_coll}"
            
        except Exception as e:
            result["status"] = "failed"
            result["message"] = str(e)
            
        return result

    def start_processor(self, processor_name: str, tier: str = None) -> Dict:
        """Start a specific processor with optional tier specification"""
        self._check_workspace_required()
        try:
            if tier:
                # Use :startWith endpoint for tier specification (correct API)
                url = f"{self.base_url}/processor/{processor_name}:startWith"
                data = {"tier": tier}
                response = requests.post(
                    url,
                    auth=self.auth,
                    headers=self.headers_v2025,
                    json=data
                )
                
                if response.status_code == 200:
                    return {
                        "name": processor_name,
                        "operation": "start",
                        "status": "started",
                        "message": f"Started successfully on tier {tier}",
                        "tier": tier
                    }
                elif response.status_code == 400:
                    # Parse error for tier requirement and retry if needed
                    error_text = response.text
                    suggested_tier = self._parse_tier_validation_error(error_text)
                    
                    if suggested_tier and suggested_tier != tier:
                        print(f"Tier {tier} insufficient, API suggests {suggested_tier}. Retrying...")
                        # Retry with suggested tier
                        retry_data = {"tier": suggested_tier}
                        retry_response = requests.post(
                            url,
                            auth=self.auth,
                            headers=self.headers_v2025,
                            json=retry_data
                        )
                        
                        if retry_response.status_code == 200:
                            return {
                                "name": processor_name,
                                "operation": "start",
                                "status": "started",
                                "message": f"Started successfully on tier {suggested_tier} (upgraded from {tier})",
                                "tier": suggested_tier
                            }
                        else:
                            print(f"Retry with {suggested_tier} also failed: {retry_response.text}")
                    else:
                        print(f"Warning: Tier specification '{tier}' failed: {error_text}")
                    
                    # Fall through to regular start
                else:
                    response.raise_for_status()
                    
            # Regular start endpoint (fallback when no tier specified)
            response = requests.post(
                f"{self.base_url}/processor/{processor_name}:start",
                auth=self.auth,
                headers=self.headers
            )
            
            response.raise_for_status()
            
            message = "Started successfully"
            if tier:
                message += " (using default tier - tier specification failed)"
                
            return {
                "name": processor_name,
                "operation": "start",
                "status": "started",
                "message": message,
                "tier": "current"
            }
            
        except requests.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_message = f"{error_message} - Response: {e.response.text}"
                except:
                    pass
            return {
                "name": processor_name,
                "operation": "start", 
                "status": "failed",
                "message": error_message,
                "http_code": getattr(e.response, 'status_code', None)
            }
    
    def stop_processor(self, processor_name: str) -> Dict:
        """Stop a specific processor"""
        self._check_workspace_required()
        try:
            response = requests.post(
                f"{self.base_url}/processor/{processor_name}:stop",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return {
                "name": processor_name,
                "operation": "stop",
                "status": "stopped",
                "message": "Stopped successfully"
            }
        except requests.RequestException as e:
            return {
                "name": processor_name,
                "operation": "stop",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }
    
    def create_processor(self, name: str, pipeline_file: str) -> Dict:
        """Create a processor from a JavaScript pipeline file"""
        try:
            # Read the pipeline from file
            pipeline_path = Path(pipeline_file)
            if not pipeline_path.exists():
                return {
                    "name": name,
                    "file": pipeline_file,
                    "operation": "create_processor",
                    "status": "failed",
                    "message": f"Pipeline file '{pipeline_file}' not found"
                }
            
            with open(pipeline_path, 'r') as f:
                pipeline_code = f.read()
            
            # First try to delete existing processor (idempotent)
            try:
                requests.delete(
                    f"{self.base_url}/processor/{name}",
                    auth=self.auth,
                    headers=self.headers
                )
            except requests.RequestException:
                pass  # Ignore delete errors
            
            # Create the processor
            payload = {
                "name": name,
                "pipeline": pipeline_code
            }
            response = requests.post(
                f"{self.base_url}/processor",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return {
                "name": name,
                "file": pipeline_file,
                "operation": "create_processor",
                "status": "created",
                "message": "Processor created successfully"
            }
            
        except requests.RequestException as e:
            return {
                "name": name,
                "file": pipeline_file,
                "operation": "create_processor",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }

    def create_processor_from_content(self, name: str, pipeline_content: str) -> Dict:
        """Create a processor from pipeline content string"""
        try:
            # First try to delete existing processor (idempotent)
            try:
                requests.delete(
                    f"{self.base_url}/processor/{name}",
                    auth=self.auth,
                    headers=self.headers
                )
            except requests.RequestException:
                pass  # Ignore delete errors
            
            # Parse the JavaScript content to extract pipeline and options
            parsed_content = self._parse_js_processor_content(pipeline_content)
            
            # Create the processor with the correct payload format
            payload = {
                "name": name,
                "pipeline": parsed_content["pipeline"]
            }
            
            # Add options if they exist (like dlq configuration)
            if "options" in parsed_content:
                payload["options"] = parsed_content["options"]
            
            response = requests.post(
                f"{self.base_url}/processor",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return {
                "name": name,
                "operation": "create_processor",
                "status": "created",
                "message": "Processor created successfully"
            }
            
        except requests.RequestException as e:
            return {
                "name": name,
                "operation": "create_processor",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }
        except Exception as e:
            return {
                "name": name,
                "operation": "create_processor",
                "status": "failed",
                "message": f"Parse error: {str(e)}"
            }

    def _parse_js_processor_content(self, content: str) -> Dict:
        """Parse JavaScript processor content and convert to JSON format"""
        import json
        import re
        
        # Remove comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Find the main object - look for { ... } that contains name and pipeline
        # This is a simple approach that works for our Terraform-like format
        
        # Extract pipeline array - find pipeline: [...] 
        pipeline_match = re.search(r'pipeline:\s*(\[.*?\])', content, re.DOTALL)
        if not pipeline_match:
            raise ValueError("Could not find pipeline array in JavaScript content")
        
        pipeline_str = pipeline_match.group(1)
        
        # Convert JavaScript object syntax to JSON
        # Replace unquoted property names with quoted ones
        pipeline_str = re.sub(r'(\w+):', r'"\1":', pipeline_str)
        # Handle special MongoDB operators that start with $
        pipeline_str = re.sub(r'"(\$\w+)":', r'"\1":', pipeline_str)
        
        try:
            pipeline = json.loads(pipeline_str)
        except json.JSONDecodeError as e:
            # If direct JSON parsing fails, try a more sophisticated approach
            # For now, return the original error
            raise ValueError(f"Could not parse pipeline as JSON: {str(e)}")
        
        result = {"pipeline": pipeline}
        
        # Look for options like dlq configuration
        dlq_match = re.search(r'dlq:\s*(\{[^}]+\})', content)
        if dlq_match:
            dlq_str = dlq_match.group(1)
            # Convert to JSON format
            dlq_str = re.sub(r'(\w+):', r'"\1":', dlq_str)
            try:
                dlq_config = json.loads(dlq_str)
                result["options"] = {"dlq": dlq_config}
            except json.JSONDecodeError:
                pass  # Ignore DLQ parsing errors for now
        
        return result

    def create_processor_from_json(self, name: str, pipeline: List[Dict], options: Dict = None) -> Dict:
        """Create a processor from JSON pipeline data"""
        self._check_workspace_required()
        try:
            # First try to delete existing processor (idempotent)
            try:
                requests.delete(
                    f"{self.base_url}/processor/{name}",
                    auth=self.auth,
                    headers=self.headers
                )
            except requests.RequestException:
                pass  # Ignore delete errors
            
            # Create the processor with the correct payload format
            payload = {
                "name": name,
                "pipeline": pipeline
            }
            
            # Add options if they exist (like dlq configuration)
            if options:
                payload["options"] = options
            
            response = requests.post(
                f"{self.base_url}/processor",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return {
                "name": name,
                "operation": "create_processor",
                "status": "created",
                "message": "Processor created successfully"
            }
            
        except requests.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    error_detail = f"{str(e)} - {error_body.get('detail', error_body)}"
                except:
                    error_detail = f"{str(e)} - {e.response.text}"
            
            return {
                "name": name,
                "operation": "create_processor",
                "status": "failed",
                "message": error_detail,
                "http_code": getattr(e.response, 'status_code', None)
            }

    def update_processor(self, processor_name: str, pipeline: List[Dict], options: Dict = None) -> Dict:
        """Update a processor's pipeline definition"""
        self._check_workspace_required()
        try:
            # Update the processor with the correct payload format
            payload = {
                "pipeline": pipeline
            }
            
            # Add options if they exist (like dlq configuration)
            if options:
                payload["options"] = options
            
            response = requests.patch(
                f"{self.base_url}/processor/{processor_name}",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return {
                "name": processor_name,
                "operation": "update_processor",
                "status": "updated",
                "message": "Processor updated successfully"
            }
            
        except requests.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    error_detail = f"{str(e)} - {error_body.get('detail', error_body)}"
                except:
                    error_detail = f"{str(e)} - {e.response.text}"
            
            return {
                "name": processor_name,
                "operation": "update_processor",
                "status": "failed",
                "message": error_detail,
                "http_code": getattr(e.response, 'status_code', None)
            }

    def delete_processor(self, processor_name: str) -> Dict:
        """Delete a processor by name"""
        self._check_workspace_required()
        try:
            # Use the correct endpoint format from MongoDB documentation
            # DELETE /api/atlas/v2/groups/{groupId}/streams/{tenantName}/processor/{processorName}
            response = requests.delete(
                f"{self.base_url}/processor/{processor_name}",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            
            return {
                "name": processor_name,
                "operation": "delete_processor",
                "status": "deleted",
                "message": "Processor deleted successfully"
            }
            
        except requests.RequestException as e:
            return {
                "name": processor_name,
                "operation": "delete_processor",
                "status": "failed",
                "message": str(e),
                "http_code": getattr(e.response, 'status_code', None)
            }
    
    # Connection Operations
    def list_connections(self) -> List[Dict]:
        """Get list of all connections"""
        self._check_workspace_required()
        response = requests.get(
            f"{self.base_url}/connections",
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("results", [])
    
    def create_http_connection(self, name: str, url: str) -> Dict:
        """Create an HTTP connection"""
        self._check_workspace_required()
        try:
            payload = {
                "name": name,
                "type": "Https",
                "url": url
            }
            response = requests.post(
                f"{self.base_url}/connections",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return {
                "name": name,
                "type": "Https",
                "url": url,
                "operation": "create_connection",
                "status": "created",
                "message": "HTTP connection created successfully"
            }
        except requests.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 409:
                return {
                    "name": name,
                    "type": "Https", 
                    "url": url,
                    "operation": "create_connection",
                    "status": "already_exists",
                    "message": "HTTP connection already exists"
                }
            return {
                "name": name,
                "type": "Https",
                "url": url,
                "operation": "create_connection",
                "status": "failed",
                "message": str(e),
                "http_code": status_code
            }
    
    def create_cluster_connection(self, name: str, cluster_name: str, db_role: Dict = None) -> Dict:
        """Create a MongoDB cluster connection"""
        self._check_workspace_required()
        try:
            payload = {
                "name": name,
                "type": "Cluster",
                "clusterName": cluster_name
            }
            
            # Add database role if provided
            if db_role:
                payload["dbRoleToExecute"] = db_role
            else:
                # Default role if none provided
                payload["dbRoleToExecute"] = {
                    "role": "atlasAdmin",
                    "type": "BUILT_IN"
                }
            response = requests.post(
                f"{self.base_url}/connections",
                auth=self.auth,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return {
                "name": name,
                "type": "Cluster",
                "clusterName": cluster_name,
                "operation": "create_connection",
                "status": "created",
                "message": "Cluster connection created successfully"
            }
        except requests.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 409:
                return {
                    "name": name,
                    "type": "Cluster",
                    "clusterName": cluster_name,
                    "operation": "create_connection",
                    "status": "already_exists",
                    "message": "Cluster connection already exists"
                }
            return {
                "name": name,
                "type": "Cluster",
                "clusterName": cluster_name,
                "operation": "create_connection",
                "status": "failed",
                "message": self._get_detailed_error(e),
                "http_code": status_code
            }

    def delete_connection(self, connection_name: str) -> Dict:
        """Delete a connection"""
        self._check_workspace_required()
        try:
            response = requests.delete(
                f"{self.base_url}/connections/{connection_name}",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return {
                "name": connection_name,
                "operation": "delete_connection",
                "status": "deleted",
                "message": "Connection deleted successfully"
            }
        except requests.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 404:
                return {
                    "name": connection_name,
                    "operation": "delete_connection",
                    "status": "not_found",
                    "message": "Connection not found"
                }
            return {
                "name": connection_name,
                "operation": "delete_connection",
                "status": "failed",
                "message": str(e),
                "http_code": status_code
            }

    # Profiling Methods
    def profile_processors(self, processor_names: List[str], duration: int, interval: int, 
                          metrics: List[str], thresholds: Dict = None) -> Dict:
        """Profile processors over a specified time period"""
        import time
        
        start_time = time.time()
        samples = []
        thresholds = thresholds or {}
        
        print(f"Collecting samples every {interval}s for {duration}s...")
        
        sample_count = 0
        while time.time() - start_time < duration:
            timestamp = datetime.now(timezone.utc).isoformat()
            sample = {"timestamp": timestamp, "processors": [], "alerts": []}
            
            for processor_name in processor_names:
                try:
                    stats_result = self.get_single_processor_stats(processor_name, verbose=True)
                    if stats_result["summary"]["success"] > 0:
                        stats = stats_result["processors"][0]["stats"]
                        
                        # Extract key metrics
                        proc_sample = {
                            "name": processor_name,
                            "memory_mb": stats.get("memoryUsageBytes", 0) / 1_048_576,
                            "input_count": stats.get("inputMessageCount", 0),
                            "output_count": stats.get("outputMessageCount", 0),
                            "dlq_count": stats.get("dlqMessageCount", 0),
                            "latency_p50_us": stats.get("latency", {}).get("p50", 0),
                            "latency_p99_us": stats.get("latency", {}).get("p99", 0),
                            "state_size_bytes": stats.get("stateSize", 0),
                            "scale_factor": stats.get("scaleFactor", 1)
                        }
                        
                        # Calculate throughput if we have previous sample
                        if len(samples) > 0:
                            prev_sample = next((p for p in samples[-1]["processors"] if p["name"] == processor_name), None)
                            if prev_sample:
                                input_diff = proc_sample["input_count"] - prev_sample["input_count"]
                                proc_sample["throughput_per_sec"] = max(0, input_diff / interval)
                            else:
                                proc_sample["throughput_per_sec"] = 0
                        else:
                            proc_sample["throughput_per_sec"] = 0
                        
                        sample["processors"].append(proc_sample)
                        
                        # Check thresholds
                        alerts = self._check_thresholds(proc_sample, thresholds)
                        sample["alerts"].extend(alerts)
                        
                except Exception as e:
                    sample["processors"].append({
                        "name": processor_name,
                        "error": str(e)
                    })
            
            samples.append(sample)
            sample_count += 1
            
            # Show progress
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            print(f"Sample {sample_count}: {remaining:.0f}s remaining...")
            
            if remaining > interval:
                time.sleep(interval)
            elif remaining > 0:
                time.sleep(remaining)
        
        return self._analyze_profile_data(samples, duration, interval)

    def profile_processors_continuous(self, processor_names: List[str], interval: int, 
                                    metrics: List[str], thresholds: Dict = None) -> Dict:
        """Continuously profile processors until interrupted"""
        import time
        
        samples = []
        thresholds = thresholds or {}
        start_time = time.time()
        
        try:
            sample_count = 0
            while True:
                timestamp = datetime.now(timezone.utc).isoformat()
                sample = {"timestamp": timestamp, "processors": [], "alerts": []}
                
                for processor_name in processor_names:
                    try:
                        stats_result = self.get_single_processor_stats(processor_name, verbose=True)
                        if stats_result["summary"]["success"] > 0:
                            stats = stats_result["processors"][0]["stats"]
                            
                            proc_sample = {
                                "name": processor_name,
                                "memory_mb": stats.get("memoryUsageBytes", 0) / 1_048_576,
                                "input_count": stats.get("inputMessageCount", 0),
                                "output_count": stats.get("outputMessageCount", 0),
                                "latency_p50_us": stats.get("latency", {}).get("p50", 0),
                                "latency_p99_us": stats.get("latency", {}).get("p99", 0)
                            }
                            
                            # Calculate throughput
                            if len(samples) > 0:
                                prev_sample = next((p for p in samples[-1]["processors"] if p["name"] == processor_name), None)
                                if prev_sample:
                                    input_diff = proc_sample["input_count"] - prev_sample["input_count"]
                                    proc_sample["throughput_per_sec"] = max(0, input_diff / interval)
                                else:
                                    proc_sample["throughput_per_sec"] = 0
                            else:
                                proc_sample["throughput_per_sec"] = 0
                            
                            sample["processors"].append(proc_sample)
                            
                            # Check thresholds and print alerts immediately
                            alerts = self._check_thresholds(proc_sample, thresholds)
                            for alert in alerts:
                                print(f"🚨 ALERT: {alert}")
                            sample["alerts"].extend(alerts)
                            
                    except Exception as e:
                        sample["processors"].append({"name": processor_name, "error": str(e)})
                
                samples.append(sample)
                sample_count += 1
                
                # Print live stats
                elapsed = time.time() - start_time
                print(f"\n=== Sample {sample_count} ({elapsed:.0f}s elapsed) ===")
                for proc in sample["processors"]:
                    if "error" not in proc:
                        print(f"{proc['name']}: "
                              f"Memory: {proc['memory_mb']:.1f}MB, "
                              f"Latency: p50={proc['latency_p50_us']/1000:.1f}ms, "
                              f"Throughput: {proc['throughput_per_sec']:.1f}/sec")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            elapsed = time.time() - start_time
            return self._analyze_profile_data(samples, elapsed, interval)

    def _check_thresholds(self, proc_sample: Dict, thresholds: Dict) -> List[str]:
        """Check if processor metrics exceed defined thresholds"""
        alerts = []
        proc_name = proc_sample["name"]
        
        if "memory_mb" in thresholds and proc_sample.get("memory_mb", 0) > thresholds["memory_mb"]:
            alerts.append(f"{proc_name}: High memory usage ({proc_sample['memory_mb']:.1f}MB > {thresholds['memory_mb']}MB)")
        
        if "latency_p99_ms" in thresholds:
            p99_ms = proc_sample.get("latency_p99_us", 0) / 1000
            if p99_ms > thresholds["latency_p99_ms"]:
                alerts.append(f"{proc_name}: High latency ({p99_ms:.1f}ms > {thresholds['latency_p99_ms']}ms)")
        
        if "throughput_min" in thresholds and proc_sample.get("throughput_per_sec", 0) < thresholds["throughput_min"]:
            alerts.append(f"{proc_name}: Low throughput ({proc_sample['throughput_per_sec']:.1f}/sec < {thresholds['throughput_min']}/sec)")
        
        return alerts

    def _analyze_profile_data(self, samples: List[Dict], duration: float, interval: int) -> Dict:
        """Analyze profiling data for trends and insights"""
        if not samples:
            return {"error": "No samples collected"}
        
        analysis = {
            "profile_summary": {
                "start_time": samples[0]["timestamp"],
                "end_time": samples[-1]["timestamp"],
                "duration_seconds": duration,
                "sample_count": len(samples),
                "interval_seconds": interval
            },
            "processors": {},
            "alerts": []
        }
        
        # Collect all alerts
        for sample in samples:
            analysis["alerts"].extend(sample.get("alerts", []))
        
        # Per-processor analysis
        if samples and samples[0]["processors"]:
            for processor_name in [p["name"] for p in samples[0]["processors"] if "error" not in p]:
                proc_data = []
                for sample in samples:
                    proc_sample = next((p for p in sample["processors"] if p["name"] == processor_name and "error" not in p), None)
                    if proc_sample:
                        proc_data.append(proc_sample)
                
                if proc_data:
                    analysis["processors"][processor_name] = self._calculate_processor_stats(proc_data)
        
        return analysis

    def _calculate_processor_stats(self, proc_data: List[Dict]) -> Dict:
        """Calculate statistics for a single processor's profile data"""
        memory_values = [p["memory_mb"] for p in proc_data]
        latency_p50_values = [p["latency_p50_us"]/1000 for p in proc_data]  # Convert to ms
        latency_p99_values = [p["latency_p99_us"]/1000 for p in proc_data]  # Convert to ms
        throughput_values = [p.get("throughput_per_sec", 0) for p in proc_data]
        
        def safe_stats(values):
            if not values or all(v == 0 for v in values):
                return {"min": 0, "max": 0, "avg": 0, "trend": "stable"}
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "trend": self._calculate_trend(values)
            }
        
        stats = {
            "memory_mb": safe_stats(memory_values),
            "latency_p50_ms": safe_stats(latency_p50_values),
            "latency_p99_ms": safe_stats(latency_p99_values),
            "throughput_per_sec": safe_stats(throughput_values),
            "samples": len(proc_data)
        }
        
        # Add recommendations
        stats["recommendations"] = self._generate_recommendations(stats)
        
        return stats

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if not first_half or not second_half:
            return "stable"
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        change_pct = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
        
        if abs(change_pct) < 5:
            return "stable"
        elif change_pct > 5:
            return "increasing"
        else:
            return "decreasing"

    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Generate performance recommendations based on profile statistics"""
        recommendations = []
        
        memory_stats = stats.get("memory_mb", {})
        latency_stats = stats.get("latency_p99_ms", {})
        throughput_stats = stats.get("throughput_per_sec", {})
        
        # Memory recommendations
        if memory_stats.get("trend") == "increasing":
            recommendations.append("Memory usage is increasing - monitor for potential memory leaks")
        elif memory_stats.get("max", 0) > 1000:
            recommendations.append("High memory usage detected - consider increasing tier or optimizing processor")
        elif memory_stats.get("avg", 0) < 100:
            recommendations.append("Low memory usage - processor may be over-provisioned")
        
        # Latency recommendations
        if latency_stats.get("trend") == "increasing":
            recommendations.append("Latency is increasing - check for performance degradation")
        elif latency_stats.get("avg", 0) > 50:
            recommendations.append("High average latency - consider tier upgrade or optimization")
        
        # Throughput recommendations
        if throughput_stats.get("trend") == "decreasing":
            recommendations.append("Throughput is decreasing - investigate potential bottlenecks")
        elif throughput_stats.get("avg", 0) < 1:
            recommendations.append("Low throughput detected - verify data source and processing logic")
        
        if not recommendations:
            recommendations.append("Processor performance appears healthy")
        
        return recommendations

    def check_collection(self, database: str, collection: str, limit: int = 3) -> Dict:
        """Check a MongoDB collection using credentials from config"""
        try:
            from pymongo import MongoClient
            import json
            from datetime import datetime
            
            # Get MongoDB connection string from config
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "check_collection",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            # Clean up the URL (remove quotes if present)
            target_url = target_url.strip('"')
            
            # Connect to MongoDB
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            # Get document count
            count = coll.count_documents({})
            
            result = {
                "database": database,
                "collection": collection,
                "operation": "check_collection", 
                "status": "success",
                "total_documents": count,
                "connection_url": target_url.split('@')[1] if '@' in target_url else "hidden"  # Hide credentials
            }
            
            if count > 0:
                # Get latest documents
                latest_docs = list(coll.find({}).sort("_id", -1).limit(limit))
                
                # Convert ObjectIds to strings for JSON serialization
                for doc in latest_docs:
                    if '_id' in doc:
                        doc['_id'] = str(doc['_id'])
                
                result["latest_documents"] = latest_docs
                
                # Check for specific processor documents if applicable
                processor_count = coll.count_documents({"processor_name": {"$exists": True}})
                if processor_count > 0:
                    result["processor_documents"] = processor_count
            
            client.close()
            return result
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "check_collection",
                "status": "failed", 
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "check_collection",
                "status": "failed",
                "message": f"Error connecting to MongoDB: {str(e)}"
            }

    def set_pre_post_images(self, database: str, collection: str, enabled: bool = True) -> Dict:
        """Enable or disable changeStreamPreAndPostImages on a collection"""
        try:
            from pymongo import MongoClient
            
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "set_pre_post_images",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            target_url = target_url.strip('"')
            client = MongoClient(target_url)
            db = client[database]
            
            # Use collMod to enable/disable changeStreamPreAndPostImages
            result = db.command("collMod", collection, changeStreamPreAndPostImages={"enabled": enabled})
            
            client.close()
            return {
                "database": database,
                "collection": collection,
                "operation": "set_pre_post_images",
                "status": "success",
                "enabled": enabled,
                "message": f"changeStreamPreAndPostImages {'enabled' if enabled else 'disabled'} on {database}.{collection}"
            }
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "set_pre_post_images",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "set_pre_post_images",
                "status": "failed",
                "message": f"Error setting pre/post images: {str(e)}"
            }

    def list_indexes(self, database: str, collection: str) -> Dict:
        """List all indexes on a MongoDB collection"""
        try:
            from pymongo import MongoClient
            
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "list_indexes",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            target_url = target_url.strip('"')
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            indexes = list(coll.list_indexes())
            
            # Clean up for JSON serialization
            for idx in indexes:
                if 'v' in idx:
                    idx['v'] = int(idx['v'])
            
            client.close()
            return {
                "database": database,
                "collection": collection,
                "operation": "list_indexes",
                "status": "success",
                "count": len(indexes),
                "indexes": indexes
            }
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "list_indexes",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "list_indexes",
                "status": "failed",
                "message": f"Error listing indexes: {str(e)}"
            }

    def create_index(self, database: str, collection: str, keys: Dict, unique: bool = False, name: str = None) -> Dict:
        """Create an index on a MongoDB collection"""
        try:
            from pymongo import MongoClient, ASCENDING, DESCENDING
            
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "create_index",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            target_url = target_url.strip('"')
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            # Convert keys dict to list of tuples for pymongo
            index_keys = [(k, v) for k, v in keys.items()]
            
            # Build index options
            options = {"unique": unique}
            if name:
                options["name"] = name
            
            index_name = coll.create_index(index_keys, **options)
            
            client.close()
            return {
                "database": database,
                "collection": collection,
                "operation": "create_index",
                "status": "success",
                "index_name": index_name,
                "keys": keys,
                "unique": unique
            }
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "create_index",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "create_index",
                "status": "failed",
                "message": f"Error creating index: {str(e)}"
            }

    def drop_index(self, database: str, collection: str, index_name: str) -> Dict:
        """Drop an index from a MongoDB collection"""
        try:
            from pymongo import MongoClient
            
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "drop_index",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            target_url = target_url.strip('"')
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            coll.drop_index(index_name)
            
            client.close()
            return {
                "database": database,
                "collection": collection,
                "operation": "drop_index",
                "status": "success",
                "dropped_index": index_name
            }
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "drop_index",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "drop_index",
                "status": "failed",
                "message": f"Error dropping index: {str(e)}"
            }

    def delete_one(self, database: str, collection: str, filter_doc: Dict = None) -> Dict:
        """Delete a single document from a MongoDB collection"""
        try:
            from pymongo import MongoClient
            
            # Get MongoDB connection string from config
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "deleteOne",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            # Clean up the URL
            target_url = target_url.strip('"')
            
            # Connect to MongoDB
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            # Default filter to empty dict (deletes first document)
            if filter_doc is None:
                filter_doc = {}
            
            # Find the document first to show what was deleted
            doc_to_delete = coll.find_one(filter_doc)
            
            if doc_to_delete:
                # Delete the document
                result = coll.delete_one(filter_doc)
                
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc_to_delete:
                    doc_to_delete['_id'] = str(doc_to_delete['_id'])
                
                response = {
                    "database": database,
                    "collection": collection,
                    "operation": "deleteOne",
                    "status": "success",
                    "deleted_count": result.deleted_count,
                    "filter": filter_doc,
                    "deleted_document": doc_to_delete
                }
            else:
                response = {
                    "database": database,
                    "collection": collection,
                    "operation": "deleteOne",
                    "status": "success",
                    "deleted_count": 0,
                    "filter": filter_doc,
                    "message": "No document matched the filter"
                }
            
            client.close()
            return response
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "deleteOne",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "deleteOne",
                "status": "failed",
                "message": f"Error deleting document: {str(e)}"
            }

    def insert_one(self, database: str, collection: str, document: Dict) -> Dict:
        """Insert a single document into a MongoDB collection"""
        try:
            from pymongo import MongoClient
            from datetime import datetime
            
            # Get MongoDB connection string from config
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "insertOne",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            # Clean up the URL
            target_url = target_url.strip('"')
            
            # Connect to MongoDB
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            # Insert the document
            result = coll.insert_one(document)
            
            response = {
                "database": database,
                "collection": collection,
                "operation": "insertOne",
                "status": "success",
                "inserted_id": str(result.inserted_id),
                "document": {k: str(v) if hasattr(v, '__str__') and not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v for k, v in document.items()}
            }
            
            client.close()
            return response
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "insertOne",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "insertOne",
                "status": "failed",
                "message": f"Error inserting document: {str(e)}"
            }

    def query_collection(self, database: str, collection: str, filter_doc: Dict = None, projection: Dict = None, limit: int = 100) -> Dict:
        """Query documents from a MongoDB collection"""
        try:
            from pymongo import MongoClient
            from datetime import datetime
            
            # Get MongoDB connection string from config
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "query_collection",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                }
            
            # Clean up the URL
            target_url = target_url.strip('"')
            
            # Connect to MongoDB
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            # Default filter to empty dict
            if filter_doc is None:
                filter_doc = {}
            
            # Execute query
            cursor = coll.find(filter_doc, projection).limit(limit)
            documents = list(cursor)
            
            # Convert ObjectIds to strings for JSON serialization
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            result = {
                "database": database,
                "collection": collection,
                "operation": "query_collection",
                "status": "success",
                "filter": filter_doc,
                "limit": limit,
                "returned": len(documents),
                "documents": documents
            }
            
            client.close()
            return result
            
        except ImportError:
            return {
                "database": database,
                "collection": collection,
                "operation": "query_collection",
                "status": "failed",
                "message": "pymongo not installed. Run: pip install pymongo"
            }
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "query_collection",
                "status": "failed",
                "message": f"Error querying MongoDB: {str(e)}"
            }

    def list_materialized_views(self, database: str = None) -> Dict:
        """List materialized views by finding MV_ prefixed collections with matching stream processors"""
        result = {
            "operation": "list_materialized_views",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "materialized_views": [],
            "summary": {
                "total": 0,
                "in_sync": 0,
                "collection_only": 0,
                "processor_only": 0,
                "by_database": {}
            },
            "debug_info": []
        }
        
        try:
            # Get all processors and filter for MV_ prefix
            processors_list = self.list_processors()
            mv_processors = {}
            for p in processors_list:
                if p["name"].startswith("MV_"):
                    mv_processors[p["name"]] = p.get("status", "UNKNOWN")
            
            result["debug_info"].append(f"Found {len(mv_processors)} MV_ processors: {list(mv_processors.keys())}")
            
            # Get collections from specified database or common databases
            if database:
                databases_to_check = [database]
            else:
                # Check common database names
                databases_to_check = ["analytics", "streams", "sample_stream_solar", "bulk_test_source", "bulk_test_sink"]
            
            all_mv_collections = {}
            
            # Check each database for MV_ collections
            for db_name in databases_to_check:
                try:
                    collections_response = self.list_database_collections(db_name)
                    if collections_response.get("status") == "success":
                        collections = collections_response.get("collections", [])
                        mv_collections_in_db = [c for c in collections if c.startswith("MV_")]
                        
                        for collection_name in mv_collections_in_db:
                            all_mv_collections[f"{db_name}.{collection_name}"] = {
                                "db": db_name,
                                "collection": collection_name
                            }
                        
                        result["debug_info"].append(f"Database {db_name}: Found {len(mv_collections_in_db)} MV_ collections: {mv_collections_in_db}")
                        
                except Exception as e:
                    result["debug_info"].append(f"Error checking database {db_name}: {str(e)}")
                    continue
            
            # Now match collections with processors
            all_mv_names = set()
            
            # Add all MV_ processor names
            all_mv_names.update(mv_processors.keys())
            
            # Add all MV_ collection names (without db prefix)
            for full_name, info in all_mv_collections.items():
                all_mv_names.add(info["collection"])
            
            result["debug_info"].append(f"All unique MV_ names found: {sorted(all_mv_names)}")
            
            # Create materialized view entries for each MV_ name
            for mv_name in all_mv_names:
                has_processor = mv_name in mv_processors
                
                # Find collections for this MV name
                matching_collections = []
                for full_name, info in all_mv_collections.items():
                    if info["collection"] == mv_name:
                        # Get document count for this collection
                        try:
                            count_result = self.check_collection(info["db"], mv_name)
                            doc_count = count_result.get("total_documents", "unknown") if count_result.get("status") == "success" else "error"
                        except:
                            doc_count = "error"
                        
                        matching_collections.append({
                            "database": info["db"],
                            "full_name": full_name,
                            "document_count": doc_count
                        })
                
                # Get full processor details including pipeline
                processor_info = {
                    "name": mv_name,
                    "status": mv_processors.get(mv_name, "NOT_FOUND"),
                    "exists": has_processor,
                    "pipeline": None
                }
                
                if has_processor:
                    try:
                        # Fetch full processor details including pipeline
                        proc_details = self.get_single_processor_stats(mv_name, verbose=True)
                        if proc_details and "processors" in proc_details and proc_details["processors"]:
                            proc_data = proc_details["processors"][0]
                            if "pipeline" in proc_data:
                                processor_info["pipeline"] = proc_data["pipeline"]
                    except Exception as e:
                        result["debug_info"].append(f"Could not fetch pipeline for {mv_name}: {str(e)}")
                
                # Determine sync status
                if has_processor and matching_collections:
                    sync_status = "in_sync"
                    result["summary"]["in_sync"] += 1
                elif matching_collections and not has_processor:
                    sync_status = "collection_only"
                    result["summary"]["collection_only"] += 1
                elif has_processor and not matching_collections:
                    sync_status = "processor_only"
                    result["summary"]["processor_only"] += 1
                else:
                    continue  # Shouldn't happen
                
                # Extract the base name (without MV_ prefix)
                base_name = mv_name[3:] if mv_name.startswith("MV_") else mv_name
                
                materialized_view = {
                    "name": base_name,
                    "prefixed_name": mv_name,
                    "sync_status": sync_status,
                    "collections": matching_collections,
                    "processor": processor_info
                }
                
                result["materialized_views"].append(materialized_view)
                result["summary"]["total"] += 1
                
                # Update by_database count
                for col in matching_collections:
                    db_name = col["database"]
                    if db_name not in result["summary"]["by_database"]:
                        result["summary"]["by_database"][db_name] = 0
                    result["summary"]["by_database"][db_name] += 1
            
            result["status"] = "success"
            result["message"] = f"Found {result['summary']['total']} materialized views (MV_ prefixed)"
            
        except Exception as e:
            result["status"] = "failed"
            result["message"] = str(e)
            result["debug_info"].append(f"Fatal error: {str(e)}")
            
        return result

    def drop_materialized_view(self, view_name: str, database: str = None) -> Dict:
        """Drop a materialized view by removing both MongoDB collection and Stream Processing processor"""
        
        # Add MV_ prefix to match the naming convention
        prefixed_name = f"MV_{view_name}"
        
        result = {
            "view_name": view_name,
            "prefixed_name": prefixed_name,
            "database": database,
            "operation": "drop_materialized_view",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "steps": [],
            "summary": {
                "collections_dropped": 0,
                "processors_dropped": 0,
                "collections_not_found": 0,
                "processors_not_found": 0
            }
        }
        
        # Step 1: Find and drop collections with the prefixed name
        collections_found = []
        
        # Determine which databases to check
        if database:
            databases_to_check = [database]
        else:
            # Check common databases if no specific database provided
            databases_to_check = ["analytics", "streams", "sample_stream_solar", "bulk_test_source", "bulk_test_sink"]
        
        # Find collections with the prefixed name
        for db_name in databases_to_check:
            try:
                collections_response = self.list_database_collections(db_name)
                if collections_response.get("status") == "success":
                    collections = collections_response.get("collections", [])
                    if prefixed_name in collections:
                        collections_found.append(db_name)
            except Exception as e:
                result["steps"].append({
                    "step": "find_collections",
                    "status": "warning",
                    "message": f"Could not check database {db_name}: {str(e)}"
                })
        
        # Drop found collections
        for db_name in collections_found:
            try:
                from pymongo import MongoClient
                
                # Get MongoDB connection string from config
                target_url = self.config.get("TARGET_URL")
                if not target_url:
                    result["steps"].append({
                        "step": "drop_collection",
                        "status": "failed",
                        "message": f"Cannot drop collection {db_name}.{prefixed_name} - TARGET_URL not found in config"
                    })
                    continue
                
                target_url = target_url.strip('"')
                client = MongoClient(target_url)
                db = client[db_name]
                
                # Drop the collection
                collection = db[prefixed_name]
                collection.drop()
                client.close()
                
                result["steps"].append({
                    "step": "drop_collection",
                    "status": "success",
                    "message": f"Dropped MongoDB collection {db_name}.{prefixed_name}"
                })
                result["summary"]["collections_dropped"] += 1
                
            except Exception as e:
                result["steps"].append({
                    "step": "drop_collection",
                    "status": "failed", 
                    "message": f"Failed to drop collection {db_name}.{prefixed_name}: {str(e)}"
                })
        
        if not collections_found:
            result["steps"].append({
                "step": "find_collections",
                "status": "info",
                "message": f"No collections found with name {prefixed_name}"
            })
            result["summary"]["collections_not_found"] = 1
        
        # Step 2: Drop the Stream Processing processor
        try:
            # Check if processor exists first
            processors_list = self.list_processors()
            processor_exists = any(p["name"] == prefixed_name for p in processors_list)
            
            if processor_exists:
                # Delete the processor using SP API
                import requests
                
                response = requests.delete(
                    f"{self.base_url}/processor/{prefixed_name}",
                    auth=self.auth,
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    result["steps"].append({
                        "step": "drop_processor",
                        "status": "success",
                        "message": f"Dropped Stream Processing processor {prefixed_name}"
                    })
                    result["summary"]["processors_dropped"] = 1
                else:
                    result["steps"].append({
                        "step": "drop_processor",
                        "status": "failed",
                        "message": f"Failed to drop processor {prefixed_name}: HTTP {response.status_code}"
                    })
            else:
                result["steps"].append({
                    "step": "find_processor",
                    "status": "info",
                    "message": f"Processor {prefixed_name} not found"
                })
                result["summary"]["processors_not_found"] = 1
                
        except Exception as e:
            result["steps"].append({
                "step": "drop_processor",
                "status": "failed",
                "message": f"Error dropping processor {prefixed_name}: {str(e)}"
            })
        
        # Determine overall status
        total_dropped = result["summary"]["collections_dropped"] + result["summary"]["processors_dropped"]
        total_not_found = result["summary"]["collections_not_found"] + result["summary"]["processors_not_found"]
        
        if total_dropped > 0 and total_not_found == 0:
            result["status"] = "success"
            result["message"] = f"Successfully dropped materialized view {view_name} ({total_dropped} components)"
        elif total_dropped > 0:
            result["status"] = "partial"
            result["message"] = f"Partially dropped materialized view {view_name} ({total_dropped} dropped, {total_not_found} not found)"
        else:
            result["status"] = "not_found"
            result["message"] = f"Materialized view {view_name} not found (no collections or processors with name {prefixed_name})"
        
        return result

    def manage_collection_ttl(self, database: str, collection: str, seconds: int = None, field: str = "_ts") -> Dict:
        """
        Manage TTL (time-to-live) settings for a collection.
        
        Args:
            database: Database name
            collection: Collection name
            seconds: TTL in seconds. If None, removes TTL. If provided, sets TTL.
            field: Field to set TTL on (default: "_ts")
            
        Returns:
            Dict with operation result
        """
        try:
            from pymongo import MongoClient
            
            # Get MongoDB connection details from config
            target_url = self.config.get('TARGET_URL')
            if not target_url:
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "manage_ttl",
                    "status": "failed",
                    "message": "TARGET_URL not found in config"
                }
            
            # Clean up the URL (remove quotes if present)
            target_url = target_url.strip('"')
            
            # Connect to MongoDB
            client = MongoClient(target_url)
            db = client[database]
            coll = db[collection]
            
            # Get existing indexes to check for TTL
            existing_indexes = list(coll.list_indexes())
            ttl_index_name = f"{field}_ttl"
            
            if seconds is None:
                # Remove TTL - look for existing TTL index and drop it
                ttl_indexes = [idx for idx in existing_indexes 
                             if idx.get('expireAfterSeconds') is not None]
                
                if ttl_indexes:
                    for idx in ttl_indexes:
                        coll.drop_index(idx['name'])
                    
                    return {
                        "database": database,
                        "collection": collection,
                        "operation": "remove_ttl",
                        "status": "success",
                        "message": f"Removed TTL from collection {database}.{collection}",
                        "removed_indexes": [idx['name'] for idx in ttl_indexes]
                    }
                else:
                    return {
                        "database": database,
                        "collection": collection,
                        "operation": "remove_ttl",
                        "status": "success",
                        "message": f"No TTL found on collection {database}.{collection}"
                    }
            else:
                # Set TTL
                # Determine which field to use for TTL
                ttl_field = field
                
                # If no specific field was provided, try to use _ts if it exists
                if field == "_ts":  # This is the default parameter value
                    ts_exists = coll.find_one({"_ts": {"$exists": True}}) is not None
                    if ts_exists:
                        ttl_field = "_ts"
                    else:
                        # Look for other common timestamp fields
                        for candidate_field in ["timestamp", "createdAt", "created_at", "date"]:
                            if coll.find_one({candidate_field: {"$exists": True}}):
                                ttl_field = candidate_field
                                break
                        else:
                            return {
                                "database": database,
                                "collection": collection,
                                "operation": "set_ttl",
                                "status": "failed",
                                "message": f"No suitable timestamp field found. Collection has no '_ts' field and no common timestamp fields (timestamp, createdAt, created_at, date) found."
                            }
                
                # Check if the determined field exists in collection
                sample_doc = coll.find_one({ttl_field: {"$exists": True}})
                if not sample_doc:
                    return {
                        "database": database,
                        "collection": collection,
                        "operation": "set_ttl",
                        "status": "failed",
                        "message": f"Field '{ttl_field}' not found in collection. Cannot set TTL on non-existent field."
                    }
                
                # Drop existing TTL index if it exists
                existing_ttl = [idx for idx in existing_indexes 
                               if idx.get('expireAfterSeconds') is not None and ttl_field in idx.get('key', {})]
                for idx in existing_ttl:
                    coll.drop_index(idx['name'])
                
                # Create new TTL index
                ttl_index_name = f"{ttl_field}_ttl"
                coll.create_index([(ttl_field, 1)], 
                                expireAfterSeconds=seconds, 
                                name=ttl_index_name)
                
                return {
                    "database": database,
                    "collection": collection,
                    "operation": "set_ttl",
                    "status": "success",
                    "message": f"Set TTL of {seconds} seconds on field '{ttl_field}' for collection {database}.{collection}",
                    "ttl_seconds": seconds,
                    "ttl_field": ttl_field,
                    "index_name": ttl_index_name
                }
                
        except Exception as e:
            return {
                "database": database,
                "collection": collection,
                "operation": "manage_ttl",
                "status": "failed",
                "message": f"Error managing TTL: {str(e)}"
            }

    def list_database_collections(self, database: str) -> Dict:
        """
        List all collections in a database.
        
        Args:
            database: Database name
            
        Returns:
            Dict with list of collections
        """
        try:
            from pymongo import MongoClient
            
            # Get MongoDB connection details from config
            target_url = self.config.get('TARGET_URL')
            if not target_url:
                return {
                    "database": database,
                    "operation": "list_collections",
                    "status": "failed",
                    "message": "TARGET_URL not found in config"
                }
            
            # Clean up the URL (remove quotes if present)
            target_url = target_url.strip('"')
            
            # Connect to MongoDB
            client = MongoClient(target_url)
            db = client[database]
            
            # Get list of collections
            collections = db.list_collection_names()
            
            return {
                "database": database,
                "operation": "list_collections",
                "status": "success",
                "collections": collections,
                "count": len(collections)
            }
                
        except Exception as e:
            return {
                "database": database,
                "operation": "list_collections",
                "status": "failed",
                "message": f"Error listing collections: {str(e)}"
            }

    def create_materialized_view(self, view_name: str, database: str, processor_file: str) -> Dict:
        """Create a materialized view by creating both a collection and stream processor with MV_ prefix"""
        
        # Add MV_ prefix to ensure proper identification
        prefixed_name = f"MV_{view_name}"
        
        result = {
            "view_name": view_name,
            "prefixed_name": prefixed_name,
            "database": database,
            "operation": "create_materialized_view",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "steps": []
        }
        
        try:
            # Step 1: Create the collection with MV_ prefix using MongoDB connection string
            from pymongo import MongoClient
            
            # Get MongoDB connection string from config
            target_url = self.config.get("TARGET_URL")
            if not target_url:
                result["steps"].append({
                    "step": "create_collection",
                    "status": "failed",
                    "message": "TARGET_URL not found in config.txt"
                })
                result["status"] = "failed"
                result["message"] = "Collection creation failed - MongoDB connection not configured"
                return result
            
            # Clean up the URL (remove quotes if present)
            target_url = target_url.strip('"')
            
            # Connect to MongoDB and create the collection
            client = MongoClient(target_url)
            db = client[database]
            collection = db[prefixed_name]
            
            # Ensure the collection exists by inserting and removing a temp document
            try:
                temp_doc = collection.insert_one({"_temp": "create_collection"})
                collection.delete_one({"_id": temp_doc.inserted_id})
                
                # Read processor config to check if $merge uses 'on' field
                # If so, create the required index
                with open(processor_file, 'r') as f:
                    processor_config = json.load(f)
                
                merge_on_field = None
                if "pipeline" in processor_config:
                    for stage in processor_config["pipeline"]:
                        if "$merge" in stage and "on" in stage["$merge"]:
                            merge_on_field = stage["$merge"]["on"]
                            break
                
                if merge_on_field:
                    # Create index on the merge key field
                    collection.create_index(merge_on_field, unique=True)
                    result["steps"].append({
                        "step": "create_collection",
                        "status": "success",
                        "message": f"Created MongoDB collection {database}.{prefixed_name} with index on {merge_on_field}"
                    })
                else:
                    result["steps"].append({
                        "step": "create_collection",
                        "status": "success",
                        "message": f"Created MongoDB collection {database}.{prefixed_name}"
                    })
            except Exception as mongo_e:
                result["steps"].append({
                    "step": "create_collection", 
                    "status": "failed",
                    "message": f"MongoDB collection creation failed: {str(mongo_e)}"
                })
                result["status"] = "failed"
                result["message"] = "Collection creation failed"
                return result
            finally:
                client.close()
        
        except Exception as e:
            result["steps"].append({
                "step": "create_collection",
                "status": "failed",
                "message": str(e)
            })
            result["status"] = "failed"
            result["message"] = "Collection creation failed"
            return result
        
        try:
            # Step 2: Modify processor config to use the prefixed collection name
            with open(processor_file, 'r') as f:
                processor_config = json.load(f)
            
            # Update the processor name and any merge targets to use prefixed names
            if "pipeline" in processor_config:
                for stage in processor_config["pipeline"]:
                    if "$merge" in stage:
                        # Update the merge target to use the prefixed collection
                        if "into" in stage["$merge"]:
                            stage["$merge"]["into"]["db"] = database
                            stage["$merge"]["into"]["coll"] = prefixed_name
            
            result["steps"].append({
                "step": "modify_processor_config",
                "status": "success",
                "message": f"Updated processor config to target {database}.{prefixed_name}"
            })
            
        except Exception as e:
            result["steps"].append({
                "step": "modify_processor_config",
                "status": "failed",
                "message": str(e)
            })
            result["status"] = "partial"
            result["message"] = "Collection created but processor config modification failed"
            return result
        
        try:
            # Step 3: Create the stream processor using Atlas Stream Processing API
            pipeline = processor_config.get("pipeline", [])
            options = processor_config.get("options", {})
            
            # Use Stream Processing API (self.base_url) to create processor
            create_result = self.create_processor_from_json(
                name=prefixed_name,  # Use prefixed name for processor too
                pipeline=pipeline,
                options=options if options else None
            )
            
            if create_result.get("status") == "created":
                result["steps"].append({
                    "step": "create_processor",
                    "status": "success",
                    "message": f"Created Stream Processing processor {prefixed_name}"
                })
                
                # Step 4: Start the processor so it begins processing data
                # Give processor a moment to validate after creation
                import time
                time.sleep(2)
                
                try:
                    start_result = self.start_processor(prefixed_name)
                    if start_result.get("status") == "started":
                        result["steps"].append({
                            "step": "start_processor",
                            "status": "success",
                            "message": f"Started processor {prefixed_name}"
                        })
                        result["status"] = "success"
                        result["message"] = f"Successfully created and started materialized view {view_name} (as {prefixed_name})"
                    else:
                        result["steps"].append({
                            "step": "start_processor",
                            "status": "failed",
                            "message": start_result.get("message", "Failed to start processor")
                        })
                        result["status"] = "partial"
                        result["message"] = "Materialized view created but processor not started"
                except Exception as start_e:
                    result["steps"].append({
                        "step": "start_processor",
                        "status": "failed",
                        "message": str(start_e)
                    })
                    result["status"] = "partial"
                    result["message"] = "Materialized view created but processor not started"
                    
            else:
                result["steps"].append({
                    "step": "create_processor", 
                    "status": "failed",
                    "message": create_result.get("message", "Failed to create processor")
                })
                result["status"] = "partial"
                result["message"] = "Collection created but processor creation failed"
                
        except Exception as e:
            result["steps"].append({
                "step": "create_processor",
                "status": "failed", 
                "message": str(e)
            })
            result["status"] = "partial"
            result["message"] = "Collection created but processor creation failed"
            
        return result

    def create_processor_from_config(self, processor_config: dict) -> Dict:
        """Create a processor from a configuration dictionary using the existing SP API"""
        try:
            # Save the processor config to a temporary file and use the existing create_processor method
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(processor_config, tmp_file, indent=2)
                tmp_file_path = tmp_file.name
            
            try:
                # Use the existing create_processor method
                result = self.create_processor(processor_config["name"], tmp_file_path)
                
                # Clean up temp file
                os.unlink(tmp_file_path)
                
                if result.get("status") == "created":
                    return {"status": "created", "message": "Processor created successfully"}
                else:
                    return {"status": "failed", "message": result.get("message", "Failed to create processor")}
                    
            except Exception as e:
                # Clean up temp file on error
                os.unlink(tmp_file_path)
                raise e
                
        except Exception as e:
            return {"status": "failed", "message": f"Error creating processor: {str(e)}"}


def main():
    """Command line interface for Atlas API operations"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Atlas Stream Processing API CLI")
    parser.add_argument("command", choices=["list", "stats", "delete", "start", "stop"], 
                       help="Command to execute")
    parser.add_argument("processor_name", nargs="?", help="Processor name for delete/start/stop commands")
    parser.add_argument("--config", default="../config.txt", help="API configuration file")
    
    args = parser.parse_args()
    
    try:
        api = AtlasStreamProcessingAPI(args.config)
        
        if args.command == "list":
            result = api.get_processor_status()
            print(colorize_json(result))
        elif args.command == "stats":
            result = api.get_processor_stats()
            print(colorize_json(result))
        elif args.command == "delete":
            if not args.processor_name:
                print(colorize_json({"error": "Processor name required for delete command"}))
                sys.exit(1)
            result = api.delete_processor(args.processor_name)
            print(colorize_json(result))
        elif args.command == "start":
            if not args.processor_name:
                print(colorize_json({"error": "Processor name required for start command"}))
                sys.exit(1)
            result = api.start_processor(args.processor_name)
            print(colorize_json(result))
        elif args.command == "stop":
            if not args.processor_name:
                print(colorize_json({"error": "Processor name required for stop command"}))
                sys.exit(1)
            result = api.stop_processor(args.processor_name)
            print(colorize_json(result))
            
    except Exception as e:
        error_result = {"error": str(e)}
        print(colorize_json(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
