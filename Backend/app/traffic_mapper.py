"""
Traffic Mapper Module
Fetches and maps network traffic from Burp Suite via burp-rest-api extension.
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import time


class TrafficMapper:
    """Manages communication with Burp Suite REST API."""
    
    def __init__(self, burp_api_url: str = "http://127.0.0.1:8090"):
        """
        Initialize the Traffic Mapper.
        
        Args:
            burp_api_url: Base URL for Burp Suite REST API
        """
        self.burp_api_url = burp_api_url.rstrip('/')
        self.last_fetch_timestamp = 0
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """Verify connection to Burp Suite API."""
        try:
            # Try to connect to Burp API
            response = requests.get(f"{self.burp_api_url}/burp/versions", timeout=2)
            if response.status_code == 200:
                print(f"✅ Connected to Burp Suite API at {self.burp_api_url}")
                return True
            else:
                print(f"⚠️  Burp Suite API returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to Burp Suite API: {e}")
            print("💡 Make sure Burp Suite is running with burp-rest-api extension on port 8090")
            return False
    
    def is_connected(self) -> bool:
        """Check if Burp Suite API is accessible."""
        return self._verify_connection()
    
    def fetch_proxy_history(self, since_timestamp: Optional[float] = None) -> List[Dict]:
        """
        Fetch HTTP requests from Burp Suite proxy history.
        
        Args:
            since_timestamp: Only fetch requests after this timestamp (Unix time)
        
        Returns:
            List of traffic log entries
        """
        try:
            # Fetch proxy history from Burp API
            # Note: The exact endpoint depends on burp-rest-api extension version
            # Common endpoints: /burp/proxy/history or /burp/target/sitemap
            response = requests.get(f"{self.burp_api_url}/burp/proxy/history", timeout=5)
            
            if response.status_code != 200:
                print(f"⚠️  Failed to fetch proxy history: {response.status_code}")
                return []
            
            history = response.json()
            
            # Filter by timestamp if specified
            if since_timestamp:
                history = [
                    entry for entry in history 
                    if entry.get('time', 0) > since_timestamp
                ]
            
            return history
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching proxy history: {e}")
            return []
    
    def fetch_recent_traffic(self, since_seconds: int = 60) -> List[Dict]:
        """
        Fetch traffic from the last N seconds.
        
        Args:
            since_seconds: Fetch traffic from the last N seconds
        
        Returns:
            List of parsed traffic entries
        """
        since_timestamp = time.time() - since_seconds
        raw_history = self.fetch_proxy_history(since_timestamp)
        
        parsed_traffic = []
        for entry in raw_history:
            parsed = self.parse_traffic_entry(entry)
            if parsed:
                parsed_traffic.append(parsed)
        
        return parsed_traffic
    
    def parse_traffic_entry(self, entry: Dict) -> Optional[Dict]:
        """
        Parse a traffic entry from Burp Suite.
        
        Args:
            entry: Raw entry from Burp Suite API
        
        Returns:
            Parsed traffic entry with standardized fields
        """
        try:
            # Extract request details
            request = entry.get('request', {})
            response = entry.get('response', {})
            
            # Parse HTTP request
            method = request.get('method', 'UNKNOWN')
            url = request.get('url', '')
            
            # Parse HTTP response
            status_code = response.get('statusCode', 0)
            
            # Get timestamp
            timestamp = entry.get('time', time.time())
            
            return {
                'burp_ref_id': entry.get('id', ''),
                'method': method,
                'url': url,
                'status_code': status_code,
                'timestamp_start': timestamp,
                'request_headers': request.get('headers', []),
                'response_headers': response.get('headers', []),
                'request_body': request.get('body', ''),
                'response_body': response.get('body', '')
            }
        except Exception as e:
            print(f"⚠️  Error parsing traffic entry: {e}")
            return None
    
    def get_traffic_by_timerange(self, start_time: float, end_time: float) -> List[Dict]:
        """
        Get traffic within a specific time range.
        
        Args:
            start_time: Start timestamp (Unix time)
            end_time: End timestamp (Unix time)
        
        Returns:
            List of traffic entries in the time range
        """
        all_history = self.fetch_proxy_history()
        
        filtered = [
            self.parse_traffic_entry(entry)
            for entry in all_history
            if start_time <= entry.get('time', 0) <= end_time
        ]
        
        return [entry for entry in filtered if entry is not None]
    
    def associate_traffic_with_edge(self, edge_id: str, start_time: float, end_time: float) -> List[Dict]:
        """
        Get all traffic associated with a specific edge (action).
        
        Args:
            edge_id: The edge ID to associate traffic with
            start_time: When the action started
            end_time: When the action ended
        
        Returns:
            List of traffic entries for this edge with edge_id added
        """
        traffic = self.get_traffic_by_timerange(start_time, end_time)
        
        # Add edge_id to each entry
        for entry in traffic:
            entry['edge_id'] = edge_id
        
        return traffic


# Singleton instance
_traffic_mapper = None

def get_traffic_mapper(burp_api_url: str = "http://127.0.0.1:8090") -> TrafficMapper:
    """Get or create the singleton Traffic Mapper instance."""
    global _traffic_mapper
    if _traffic_mapper is None:
        _traffic_mapper = TrafficMapper(burp_api_url)
    return _traffic_mapper
