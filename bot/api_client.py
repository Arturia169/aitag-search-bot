"""API client for aitag.win website."""

import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class AITagAPIClient:
    """Client for interacting with aitag.win API."""
    
    IMAGE_BASE_URL = "https://ai-img.10118899.xyz/"
    
    def __init__(self, base_url: str, timeout: int = 30, proxy_url: str = None):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the website
            timeout: Request timeout in seconds
            proxy_url: Optional proxy URL for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.proxy_url = proxy_url
        logger.info(f"APIClient initialized - base_url: {self.base_url}, timeout: {timeout}, proxy: {proxy_url}")
        
    async def search_works(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 60,
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
        
        logger.info(f"Searching: url={url}, params={params}")
        
        try:
            # Create client with or without proxy
            if self.proxy_url:
                proxy = httpx.Proxy(url=self.proxy_url)
                mounts = {
                    "http://": httpx.AsyncHTTPTransport(proxy=proxy),
                    "https://": httpx.AsyncHTTPTransport(proxy=proxy),
                }
                client = httpx.AsyncClient(mounts=mounts, timeout=float(self.timeout))
            else:
                client = httpx.AsyncClient(timeout=float(self.timeout))
            
            async with client:
                response = await client.get(url, params=params)
                
                logger.info(f"API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    works = self.extract_works(data)
                    logger.info(f"Search successful for keyword '{keyword}', page {page}, got {len(works)} results")
                    return data
                else:
                    logger.error(f"API request failed with status {response.status_code}")
                    logger.error(f"Response body: {response.text[:500]}")
                    return None
                    
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during API request: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error during API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}", exc_info=True)
            return None

    async def get_monthly_ranking(
        self,
        page: int = 1,
        page_size: int = 60,
        month: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get monthly ranking of popular works.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of results per page
            month: Optional month filter (format: YYYY-MM), if None uses current month
            
        Returns:
            Dictionary containing ranking results, or None if request fails
        """
        # Use real-time ranking if no specific month is provided
        if month:
            url = f"{self.base_url}/api/rank/monthly/fixed"
            params = {"month": month, "page": page, "page_size": page_size}
        else:
            url = f"{self.base_url}/api/rank/monthly/real"
            params = {"page": page, "page_size": page_size}
        
        logger.info(f"Fetching monthly ranking: url={url}, params={params}")
        
        try:
            if self.proxy_url:
                proxy = httpx.Proxy(url=self.proxy_url)
                mounts = {
                    "http://": httpx.AsyncHTTPTransport(proxy=proxy),
                    "https://": httpx.AsyncHTTPTransport(proxy=proxy),
                }
                client = httpx.AsyncClient(mounts=mounts, timeout=float(self.timeout))
            else:
                client = httpx.AsyncClient(timeout=float(self.timeout))
                
            async with client:
                response = await client.get(url, params=params)
                
                logger.info(f"Ranking API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    works = self.extract_works(data)
                    logger.info(f"Ranking fetch successful, got {len(works)} results")
                    return data
                else:
                    logger.error(f"Failed to fetch ranking: {response.status_code}")
                    logger.error(f"Response body: {response.text[:500]}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching ranking: {e}", exc_info=True)
            return None

    async def get_random_work(self, keyword: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch a random work from the entire library or filtered by keyword."""
        import random
        
        # Step 1: Get total count
        url = f"{self.base_url}/api/ai_works_search"
        params = {"page": 1, "page_size": 20} 
        if keyword:
            params["q"] = keyword
        
        try:
            transport = None
            if self.proxy_url:
                proxy = httpx.Proxy(url=self.proxy_url)
                transport = httpx.AsyncHTTPTransport(proxy=proxy)
                
            async with httpx.AsyncClient(transport=transport, timeout=float(self.timeout)) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.error(f"Random fetch step 1 failed: {resp.status_code}")
                    return None
                    
                data = resp.json()
                total_items = self.get_total_count(data)
                if total_items <= 0:
                    return None
                
                # Step 2: Pick a random page
                page_size = 10
                total_pages = (total_items + page_size - 1) // page_size
                max_pages = min(total_pages, 200) 
                
                for _ in range(3): # Try up to 3 times
                    random_page = random.randint(1, max_pages)
                    fetch_params = {"page": random_page, "page_size": page_size}
                    if keyword:
                        fetch_params["q"] = keyword
                        
                    resp = await client.get(url, params=fetch_params)
                    if resp.status_code == 200:
                        works = self.extract_works(resp.json())
                        if works:
                            return random.choice(works)
                
            return None
        except Exception as e:
            logger.error(f"Error fetching random work: {e}", exc_info=True)
            return None
    
    

    async def get_work_detail(self, work_id: int) -> Optional[Dict[str, Any]]:
        """Get full details for a specific work.
        
        Args:
            work_id: Work ID
            
        Returns:
            Dictionary containing work details, or None if request fails
        """
        url = f"{self.base_url}/api/work/{work_id}"
        logger.info(f"Fetching work detail: {url}")
        
        try:
            if self.proxy_url:
                proxy = httpx.Proxy(url=self.proxy_url)
                mounts = {
                    "http://": httpx.AsyncHTTPTransport(proxy=proxy),
                    "https://": httpx.AsyncHTTPTransport(proxy=proxy),
                }
                client = httpx.AsyncClient(mounts=mounts, timeout=float(self.timeout))
            else:
                client = httpx.AsyncClient(timeout=float(self.timeout))
                
            async with client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to fetch work detail {work_id}: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching work detail: {e}", exc_info=True)
            return None
    
    
    def get_work_url(self, work_id: int) -> str:
        """Get the full URL for a work.
        
        Args:
            work_id: Work ID
            
        Returns:
            Full URL to the work detail page
        """
        return f"{self.base_url}/i/{work_id}"
    
    def get_full_image_url(self, image_path: str) -> str:
        """Get the full CDN URL for an image.
        
        Args:
            image_path: Relative image path
            
        Returns:
            Full CDN URL
        """
        if not image_path:
            return ""
        if image_path.startswith("http"):
            return image_path
        return f"{self.IMAGE_BASE_URL}{image_path.lstrip('/')}"

    def get_thumbnail_url(self, work: Dict[str, Any]) -> str:
        """Construct thumbnail URL from work data if image_path is missing.
        
        Args:
            work: Work data dictionary
            
        Returns:
            Thumbnail URL
        """
        image_path = work.get("image_path")
        if image_path:
            return self.get_full_image_url(image_path)
            
        # Fallback pattern based on research
        work_id = work.get("id") or work.get("work_id") or work.get("pid")
        ai_type = work.get("AI_type") or "NAI"
        user_id = work.get("userId") or work.get("user_id")
        
        if work_id and user_id:
            return f"{self.IMAGE_BASE_URL}{ai_type}/{user_id}/{work_id}_p0.webp"
        
        return ""
    
    
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
        elif "items" in api_response:
            return api_response["items"]
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
