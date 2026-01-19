"""API client for aitag.win website."""

import logging
from typing import Optional, Dict, Any, List
import aiohttp

logger = logging.getLogger(__name__)


class AITagAPIClient:
    """Client for interacting with aitag.win API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the website
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
    async def search_works(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 10,
        sort: str = "new",
        time_range: str = "all"
    ) -> Optional[Dict[str, Any]]:
        """Search for AI artworks by keyword.
        
        Args:
            keyword: Search keyword
            page: Page number (1-indexed)
            page_size: Number of results per page
            sort: Sort order (new, hot, etc.)
            time_range: Time range filter (all, day, week, month)
            
        Returns:
            Dictionary containing search results, or None if request fails
        """
        url = f"{self.base_url}/api/ai_works_search"
        params = {
            "q": keyword,
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "time_range": time_range
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Search successful for keyword '{keyword}', page {page}")
                        return data
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error during API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            return None
    
    def get_work_url(self, work_id: int) -> str:
        """Get the full URL for a work.
        
        Args:
            work_id: Work ID
            
        Returns:
            Full URL to the work detail page
        """
        return f"{self.base_url}/i/{work_id}"
    
    @staticmethod
    def extract_works(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract work items from API response.
        
        Args:
            api_response: API response dictionary
            
        Returns:
            List of work dictionaries
        """
        if not api_response:
            return []
        
        # The API response structure may vary, adjust as needed
        # Common structures: {"data": [...]} or {"works": [...]} or direct list
        if isinstance(api_response, list):
            return api_response
        elif "data" in api_response:
            return api_response["data"]
        elif "works" in api_response:
            return api_response["works"]
        else:
            logger.warning(f"Unknown API response structure: {api_response.keys()}")
            return []
    
    @staticmethod
    def get_total_count(api_response: Dict[str, Any]) -> int:
        """Get total count of results from API response.
        
        Args:
            api_response: API response dictionary
            
        Returns:
            Total count of results
        """
        if not api_response:
            return 0
        
        # Common keys for total count
        for key in ["total", "total_count", "count"]:
            if key in api_response:
                return api_response[key]
        
        # If no total count, return length of works
        works = AITagAPIClient.extract_works(api_response)
        return len(works)
