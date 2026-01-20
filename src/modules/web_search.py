from langchain_community.tools import DuckDuckGoSearchResults, DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from typing import List, Dict, Optional
import re


class WebSearchTool:
    """Web search tool using LangChain's DuckDuckGo integration (free, no API key needed)"""
    
    def __init__(self, max_results: int = 5):
        """
        Initialize DuckDuckGo search with LangChain
        
        Args:
            max_results: Default maximum number of results
        """
        # Initialize LangChain's DuckDuckGo wrapper
        self.search_wrapper = DuckDuckGoSearchAPIWrapper(max_results=max_results)
        
        # Create LangChain tools
        self.search_tool = DuckDuckGoSearchResults(api_wrapper=self.search_wrapper)
        self.search_run = DuckDuckGoSearchRun(api_wrapper=self.search_wrapper)
        
    def search(
        self,
        query: str,
        search_type: str = "general",
        max_results: int = 5
    ) -> Dict:
        """
        Perform web search using LangChain's DuckDuckGo
        
        Args:
            query: Search query
            search_type: "alternatives", "verify_vendor", "reviews", "general"
            max_results: Number of results to return
            
        Returns:
            Dict: Search results
        """
        # Enhance query based on type
        enhanced_query = self._enhance_query(query, search_type)
        
        try:
            # Update max_results for this search
            self.search_wrapper.max_results = max_results
            
            # Perform search using LangChain tool
            raw_results = self.search_tool.run(enhanced_query)

            # Parse and format results
            results = self._parse_results(raw_results, query)
            
            return {
                "success": True,
                "query": query,
                "search_type": search_type,
                "results": results,
                "total_results": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    def find_alternatives(
        self,
        service_name: str,
        current_price: Optional[float] = None
    ) -> Dict:
        """
        Find cheaper alternatives to a service
        
        Args:
            service_name: Name of current service
            current_price: Current price (optional)
            
        Returns:
            Dict: Alternative services
        """
        query = f"cheaper alternative to {service_name} comparison 2024"
        if current_price:
            query += f" pricing under ${current_price}"
        
        return self.search(query, search_type="alternatives", max_results=5)
    
    def verify_vendor(self, vendor_name: str) -> Dict:
        """
        Verify vendor legitimacy and get info
        
        Args:
            vendor_name: Vendor to verify
            
        Returns:
            Dict: Vendor information
        """
        query = f"{vendor_name} official website contact information"
        return self.search(query, search_type="verify_vendor", max_results=3)
    
    def get_reviews(self, service_name: str) -> Dict:
        """
        Get reviews and ratings for a service
        
        Args:
            service_name: Service to get reviews for
            
        Returns:
            Dict: Reviews and ratings
        """
        query = f"{service_name} reviews ratings 2024"
        return self.search(query, search_type="reviews", max_results=5)
    
    def _enhance_query(self, query: str, search_type: str) -> str:
        """Enhance query based on search type"""
        enhancements = {
            "alternatives": f"{query} comparison pricing",
            "verify_vendor": f"{query} official",
            "reviews": f"{query} reviews ratings",
            "general": query
        }
        return enhancements.get(search_type, query)
    
    def _parse_results(self, raw_results, query: str) -> List[Dict]:
        """
        Parse LangChain DuckDuckGo results
        
        Args:
            raw_results: Raw string results from LangChain tool
            query: Original query
            
        Returns:
            List of formatted results
        """
        results = []
        
        # LangChain returns results as a string, parse it
        # Format is typically: [snippet: ..., title: ..., link: ...]
        try:
            # Coerce to string in case wrapper returns list/dict
            raw_text = raw_results if isinstance(raw_results, str) else str(raw_results)

            # Split by result separators
            result_blocks = raw_text.split('[snippet:')
            
            for i, block in enumerate(result_blocks[1:], 1):  # Skip first empty element
                try:
                    # Extract components
                    snippet_end = block.find(', title:')
                    snippet = block[:snippet_end].strip() if snippet_end > 0 else ""
                    
                    title_start = block.find('title:') + 6
                    title_end = block.find(', link:')
                    title = block[title_start:title_end].strip() if title_end > 0 else ""
                    
                    link_start = block.find('link:') + 5
                    link_end = block.find(']', link_start)
                    url = block[link_start:link_end].strip() if link_end > 0 else ""
                    
                    if title or url:
                        formatted_result = {
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'position': i
                        }
                        
                        # Try to extract price if present
                        price = self._extract_price(snippet)
                        if price:
                            formatted_result['price'] = price
                        
                        results.append(formatted_result)
                        
                except Exception as e:
                    continue
            
            return results
            
        except Exception as e:
            # Fallback: return simple format
            return [{
                'title': f"Result for: {query}",
                'url': "",
                'snippet': raw_results[:200],
                'position': 1
            }]
    
    def _extract_price(self, text: str) -> Optional[float]:
        """
        Try to extract price from text
        
        Args:
            text: Text to search for prices
            
        Returns:
            Price as float, or None
        """
        if not text:
            return None
        
        # Look for common price patterns
        patterns = [
            r'\$(\d+\.?\d*)',  # $19.99
            r'(\d+\.?\d*)\s*(?:dollars|USD)',  # 19.99 dollars
            r'(\d+\.?\d*)/(?:mo|month)',  # 19.99/mo
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        
        return None
    
    def search_news(self, query: str, max_results: int = 5) -> Dict:
        """
        Search for news articles using LangChain's DuckDuckGo
        
        Args:
            query: Search query
            max_results: Number of results
            
        Returns:
            Dict: News results
        """
        try:
            # Update max_results
            self.search_wrapper.max_results = max_results
            
            # Add "news" to query for better news results
            news_query = f"{query} news"
            
            # Search using LangChain tool
            raw_results = self.search_tool.run(news_query)

            # Parse results
            results = self._parse_results(raw_results, query)
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }