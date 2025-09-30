#!/usr/bin/env python3
"""
Real Web Search Tool

Integrates with SERPER API for actual web search capabilities.
Provides comprehensive search functionality for research agents.
"""

import os
import aiohttp
from typing import Dict, List, Any
from pydantic import BaseModel, Field
from .base_tool import BaseTool, ToolResult


class SearchResult(BaseModel):
    """Single search result model."""
    
    title: str = Field(..., description="Result title")
    link: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Result snippet/description")
    position: int = Field(..., description="Result position in search")
    
    
class WebSearchTool(BaseTool):
    """
    Real web search tool using SERPER API.
    
    Provides actual web search capabilities for research agents.
    Supports different search types and result filtering.
    """
    
    name: str = "web_search"
    description: str = "Search the web for current information using real search engines"
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or question"
            },
            "search_type": {
                "type": "string",
                "enum": ["web", "news", "academic", "images"],
                "description": "Type of search to perform",
                "default": "web"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            },
            "country": {
                "type": "string",
                "description": "Country code for localized search (e.g., 'us', 'cn', 'uk')",
                "default": "us"
            },
            "language": {
                "type": "string", 
                "description": "Language for search results (e.g., 'en', 'zh', 'zh-cn')",
                "default": "en"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
        self._api_key = api_key
        self._base_url = "https://google.serper.dev"
    
    async def execute(
        self,
        query: str,
        search_type: str = "web",
        max_results: int = 10,
        country: str = "us",
        language: str = "en",
        **kwargs
    ) -> ToolResult:
        """
        Execute web search using SERPER API.
        
        Args:
            query: Search query
            search_type: Type of search (web, news, academic, images)
            max_results: Maximum results to return
            country: Country code for localized results
            language: Language for search results
            
        Returns:
            ToolResult with formatted search results
        """
        try:
            # Map search types to SERPER endpoints
            endpoint_map = {
                "web": "/search",
                "news": "/news", 
                "academic": "/scholar",
                "images": "/images"
            }
            
            endpoint = endpoint_map.get(search_type, "/search")
            url = f"{self._base_url}{endpoint}"
            
            # Prepare search parameters
            payload = {
                "q": query,
                "num": min(max_results, 100),
                "gl": country,
                "hl": language
            }
            
            # Add type-specific parameters
            if search_type == "news":
                payload["tbs"] = "qdr:m"  # Recent month for news
            elif search_type == "academic":
                payload["as_ylo"] = "2020"  # Academic papers from 2020+
            
            headers = {
                "X-API-KEY": self._api_key,
                "Content-Type": "application/json"
            }
            
            # Execute search request
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ToolResult(
                            error=f"Search API error ({response.status}): {error_text}"
                        )
                    
                    data = await response.json()
            
            # Parse and format results
            results = self._parse_results(data, search_type, max_results)
            
            if not results:
                return ToolResult(
                    output=f"🔍 **搜索结果 - {query}**\n\n未找到相关结果。",
                    system=f"No results found for query: {query}"
                )
            
            # Format output
            output = self._format_results(query, search_type, results)
            
            return ToolResult(
                output=output,
                system=f"Found {len(results)} results for '{query}' ({search_type} search)"
            )
            
        except aiohttp.ClientError as e:
            return ToolResult(error=f"Network error during search: {str(e)}")
        except Exception as e:
            return ToolResult(error=f"Search execution failed: {str(e)}")
    
    def _parse_results(self, data: Dict[str, Any], search_type: str, max_results: int) -> List[SearchResult]:
        """Parse SERPER API response into SearchResult objects."""
        results = []
        
        # Handle different result structures based on search type
        if search_type == "web":
            organic_results = data.get("organic", [])
        elif search_type == "news":
            organic_results = data.get("news", [])
        elif search_type == "academic":
            organic_results = data.get("organic", [])
        elif search_type == "images":
            organic_results = data.get("images", [])
        else:
            organic_results = data.get("organic", [])
        
        for i, result in enumerate(organic_results[:max_results]):
            try:
                search_result = SearchResult(
                    title=result.get("title", "No title"),
                    link=result.get("link", ""),
                    snippet=result.get("snippet", result.get("description", "No description")),
                    position=i + 1
                )
                results.append(search_result)
            except Exception as e:
                # Skip malformed results
                continue
        
        return results
    
    def _format_results(self, query: str, search_type: str, results: List[SearchResult]) -> str:
        """Format search results for display."""
        
        # Search type display names
        type_names = {
            "web": "网页搜索",
            "news": "新闻搜索", 
            "academic": "学术搜索",
            "images": "图片搜索"
        }
        
        type_display = type_names.get(search_type, "网页搜索")
        
        output = [
            f"🔍 **{type_display}结果 - {query}**",
            f"📊 找到 {len(results)} 个相关结果",
            ""
        ]
        
        for result in results:
            output.extend([
                f"**{result.position}. {result.title}**",
                f"🔗 {result.link}",
                f"📝 {result.snippet}",
                ""
            ])
        
        return "\n".join(output)


class ScholarSearchTool(BaseTool):
    """
    Specialized academic search tool using SERPER Scholar API.
    
    Focuses on academic papers, citations, and research publications.
    """
    
    name: str = "scholar_search"
    description: str = "Search academic papers and scholarly articles"
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Academic search query"
            },
            "year_range": {
                "type": "string",
                "description": "Publication year range (e.g., '2020-2024')",
                "default": "2020-2024"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of papers to return",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
        self._api_key = api_key
        self._base_url = "https://google.serper.dev/scholar"
    
    async def execute(
        self,
        query: str,
        year_range: str = "2020-2024",
        max_results: int = 10,
        **kwargs
    ) -> ToolResult:
        """Execute academic search."""
        
        try:
            # Parse year range
            if "-" in year_range:
                start_year, end_year = year_range.split("-")
                year_filter = f"as_ylo={start_year.strip()}&as_yhi={end_year.strip()}"
            else:
                year_filter = f"as_ylo={year_range.strip()}"
            
            payload = {
                "q": query,
                "num": min(max_results, 50),
                "as_ylo": year_range.split("-")[0] if "-" in year_range else year_range
            }
            
            headers = {
                "X-API-KEY": self._api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self._base_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ToolResult(
                            error=f"Scholar API error ({response.status}): {error_text}"
                        )
                    
                    data = await response.json()
            
            # Parse academic results
            papers = data.get("organic", [])
            
            if not papers:
                return ToolResult(
                    output=f"🎓 **学术搜索结果 - {query}**\n\n未找到相关学术论文。",
                    system=f"No academic papers found for: {query}"
                )
            
            # Format academic results
            output = [
                f"🎓 **学术搜索结果 - {query}**",
                f"📚 时间范围: {year_range}",
                f"📊 找到 {len(papers)} 篇相关论文",
                ""
            ]
            
            for i, paper in enumerate(papers[:max_results]):
                authors = paper.get("authors", "未知作者")
                year = paper.get("year", "未知年份")
                citations = paper.get("citedBy", {}).get("total", 0)
                
                output.extend([
                    f"**{i+1}. {paper.get('title', 'No title')}**",
                    f"👨‍🎓 作者: {authors}",
                    f"📅 年份: {year} | 📈 引用数: {citations}",
                    f"🔗 {paper.get('link', '')}",
                    f"📝 {paper.get('snippet', 'No abstract available')}",
                    ""
                ])
            
            return ToolResult(
                output="\n".join(output),
                system=f"Found {len(papers)} academic papers for '{query}'"
            )
            
        except Exception as e:
            return ToolResult(error=f"Academic search failed: {str(e)}")


def create_search_tools() -> List[BaseTool]:
    """Create all search-related tools."""
    return [
        WebSearchTool(),
        ScholarSearchTool()
    ]