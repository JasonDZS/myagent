#!/usr/bin/env python3
"""
Web Content Analysis Tool

Provides web scraping, content extraction, and text analysis capabilities.
Fetches and analyzes web pages for research purposes.
"""

import asyncio
import aiohttp
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json
from bs4 import BeautifulSoup
from .base_tool import BaseTool, ToolResult


class WebContentTool(BaseTool):
    """
    Real web content extraction and analysis tool.
    
    Fetches web pages, extracts text content, and performs basic analysis.
    """
    
    name: str = "fetch_content"
    description: str = "Fetch and analyze web page content, extract text, links, and metadata"
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the web page to fetch and analyze"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["basic", "detailed", "text_only", "links", "metadata"],
                "description": "Type of content analysis to perform",
                "default": "basic"
            },
            "extract_links": {
                "type": "boolean",
                "description": "Whether to extract and analyze links",
                "default": True
            },
            "max_text_length": {
                "type": "integer",
                "description": "Maximum length of extracted text content",
                "default": 5000,
                "minimum": 100,
                "maximum": 20000
            },
            "follow_redirects": {
                "type": "boolean",
                "description": "Whether to follow HTTP redirects",
                "default": True
            }
        },
        "required": ["url"]
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Research-Agent/1.0; +http://research-bot.example.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive"
        }
    
    async def execute(
        self,
        url: str,
        analysis_type: str = "basic",
        extract_links: bool = True,
        max_text_length: int = 5000,
        follow_redirects: bool = True,
        **kwargs
    ) -> ToolResult:
        """
        Fetch and analyze web page content.
        
        Args:
            url: URL to fetch
            analysis_type: Type of analysis to perform
            extract_links: Whether to extract links
            max_text_length: Maximum text content length
            follow_redirects: Whether to follow redirects
            
        Returns:
            ToolResult with content analysis
        """
        try:
            # Validate URL
            if not self._is_valid_url(url):
                return ToolResult(error=f"Invalid URL format: {url}")
            
            # Fetch web page content
            content_data = await self._fetch_page_content(
                url, follow_redirects, max_text_length
            )
            
            if "error" in content_data:
                return ToolResult(error=content_data["error"])
            
            # Perform requested analysis
            if analysis_type == "text_only":
                result = self._analyze_text_only(content_data)
            elif analysis_type == "links":
                result = self._analyze_links_only(content_data)
            elif analysis_type == "metadata":
                result = self._analyze_metadata_only(content_data)
            elif analysis_type == "detailed":
                result = self._analyze_detailed(content_data, extract_links)
            else:  # basic
                result = self._analyze_basic(content_data, extract_links)
            
            # Format output
            output = self._format_content_analysis(url, analysis_type, result)
            
            return ToolResult(
                output=output,
                system=f"Successfully analyzed web content from {url}"
            )
            
        except Exception as e:
            return ToolResult(error=f"Web content analysis failed: {str(e)}")
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def _fetch_page_content(
        self, 
        url: str, 
        follow_redirects: bool,
        max_content_length: int
    ) -> Dict[str, Any]:
        """Fetch and parse web page content."""
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)  # For development, handle SSL issues
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(
                headers=self._headers,
                connector=connector,
                timeout=timeout
            ) as session:
                
                # Configure redirect behavior
                allow_redirects = follow_redirects
                
                async with session.get(url, allow_redirects=allow_redirects) as response:
                    # Check response status
                    if response.status >= 400:
                        return {"error": f"HTTP {response.status}: Failed to fetch {url}"}
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'html' not in content_type and 'xml' not in content_type:
                        return {"error": f"Unsupported content type: {content_type}"}
                    
                    # Read content with size limit
                    content = await response.read()
                    if len(content) > max_content_length * 10:  # Rough size check
                        content = content[:max_content_length * 10]
                    
                    # Decode content
                    try:
                        html_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            html_content = content.decode('latin1')
                        except UnicodeDecodeError:
                            html_content = content.decode('utf-8', errors='ignore')
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    return {
                        "url": str(response.url),  # Final URL after redirects
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content_type": content_type,
                        "soup": soup,
                        "raw_html": html_content[:max_content_length],
                        "size": len(content)
                    }
                    
        except aiohttp.ClientError as e:
            return {"error": f"Network error: {str(e)}"}
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": f"Failed to fetch content: {str(e)}"}
    
    def _analyze_text_only(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and analyze only text content."""
        
        soup = content_data["soup"]
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text()
        
        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_cleaned = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Basic text analysis
        word_count = len(text_cleaned.split())
        char_count = len(text_cleaned)
        line_count = len(text_cleaned.splitlines())
        
        return {
            "text_content": text_cleaned[:content_data.get("max_length", 5000)],
            "word_count": word_count,
            "character_count": char_count,
            "line_count": line_count,
            "is_truncated": len(text_cleaned) > content_data.get("max_length", 5000)
        }
    
    def _analyze_links_only(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and analyze only links."""
        
        soup = content_data["soup"]
        base_url = content_data["url"]
        
        links = []
        
        # Extract all links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True)
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Classify link type
            if href.startswith('#'):
                link_type = 'anchor'
            elif href.startswith('mailto:'):
                link_type = 'email'
            elif href.startswith('tel:'):
                link_type = 'phone'
            elif urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                link_type = 'internal'
            else:
                link_type = 'external'
            
            links.append({
                "url": absolute_url,
                "text": text,
                "type": link_type,
                "raw_href": href
            })
        
        # Analyze link statistics
        link_stats = {
            "total_links": len(links),
            "internal_links": len([l for l in links if l["type"] == "internal"]),
            "external_links": len([l for l in links if l["type"] == "external"]),
            "anchor_links": len([l for l in links if l["type"] == "anchor"]),
            "email_links": len([l for l in links if l["type"] == "email"])
        }
        
        return {
            "links": links[:50],  # Limit to first 50 links
            "link_statistics": link_stats,
            "total_found": len(links)
        }
    
    def _analyze_metadata_only(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only metadata from the page."""
        
        soup = content_data["soup"]
        
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        metadata["title"] = title_tag.get_text().strip() if title_tag else "No title"
        
        # Meta tags
        meta_tags = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_tags[name] = content
        
        metadata["meta_tags"] = meta_tags
        
        # Description
        metadata["description"] = (
            meta_tags.get('description') or 
            meta_tags.get('og:description') or 
            "No description"
        )
        
        # Keywords
        metadata["keywords"] = meta_tags.get('keywords', "")
        
        # Open Graph data
        og_data = {k: v for k, v in meta_tags.items() if k.startswith('og:')}
        metadata["open_graph"] = og_data
        
        # Twitter Card data
        twitter_data = {k: v for k, v in meta_tags.items() if k.startswith('twitter:')}
        metadata["twitter_card"] = twitter_data
        
        # Language
        html_tag = soup.find('html')
        metadata["language"] = html_tag.get('lang') if html_tag else "unknown"
        
        # Headings structure
        headings = []
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            for h in h_tags:
                headings.append({
                    "level": i,
                    "text": h.get_text().strip()
                })
        
        metadata["headings"] = headings[:20]  # First 20 headings
        
        return metadata
    
    def _analyze_basic(self, content_data: Dict[str, Any], extract_links: bool) -> Dict[str, Any]:
        """Perform basic content analysis."""
        
        result = {}
        
        # Get text content
        text_analysis = self._analyze_text_only(content_data)
        result["text"] = {
            "preview": text_analysis["text_content"][:1000],
            "word_count": text_analysis["word_count"],
            "character_count": text_analysis["character_count"]
        }
        
        # Get basic metadata
        metadata = self._analyze_metadata_only(content_data)
        result["metadata"] = {
            "title": metadata["title"],
            "description": metadata["description"],
            "language": metadata["language"]
        }
        
        # Get links if requested
        if extract_links:
            link_analysis = self._analyze_links_only(content_data)
            result["links"] = {
                "total_links": link_analysis["link_statistics"]["total_links"],
                "external_links": link_analysis["link_statistics"]["external_links"],
                "top_links": link_analysis["links"][:10]
            }
        
        # Page info
        result["page_info"] = {
            "final_url": content_data["url"],
            "status_code": content_data["status_code"],
            "content_type": content_data["content_type"],
            "size_bytes": content_data["size"]
        }
        
        return result
    
    def _analyze_detailed(self, content_data: Dict[str, Any], extract_links: bool) -> Dict[str, Any]:
        """Perform detailed content analysis."""
        
        result = {}
        
        # Full text analysis
        result["text"] = self._analyze_text_only(content_data)
        
        # Full metadata
        result["metadata"] = self._analyze_metadata_only(content_data)
        
        # Links analysis if requested
        if extract_links:
            result["links"] = self._analyze_links_only(content_data)
        
        # Additional analysis
        soup = content_data["soup"]
        
        # Images
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            alt = img.get('alt', '')
            if src:
                absolute_src = urljoin(content_data["url"], src)
                images.append({
                    "src": absolute_src,
                    "alt": alt,
                    "title": img.get('title', '')
                })
        
        result["images"] = {
            "total_images": len(images),
            "images": images[:20]  # First 20 images
        }
        
        # Tables
        tables = []
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            table_data = {
                "rows": len(rows),
                "columns": len(rows[0].find_all(['th', 'td'])) if rows else 0,
                "has_header": bool(table.find('th'))
            }
            tables.append(table_data)
        
        result["tables"] = {
            "total_tables": len(tables),
            "tables": tables
        }
        
        # Page structure
        result["structure"] = {
            "has_navigation": bool(soup.find('nav')),
            "has_header": bool(soup.find('header')),
            "has_footer": bool(soup.find('footer')),
            "has_main": bool(soup.find('main')),
            "sections": len(soup.find_all('section')),
            "articles": len(soup.find_all('article'))
        }
        
        return result
    
    def _format_content_analysis(self, url: str, analysis_type: str, result: Dict[str, Any]) -> str:
        """Format content analysis results for display."""
        
        analysis_names = {
            "basic": "基础内容分析",
            "detailed": "详细内容分析",
            "text_only": "文本内容提取",
            "links": "链接分析",
            "metadata": "元数据分析"
        }
        
        output = [
            f"🌐 **{analysis_names.get(analysis_type, '网页内容分析')}**",
            f"🔗 URL: {url}",
            f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        if analysis_type == "text_only":
            text = result
            output.extend([
                f"📝 **文本内容分析**",
                f"• 字符数: {text['character_count']:,}",
                f"• 单词数: {text['word_count']:,}",
                f"• 行数: {text['line_count']:,}",
                f"• 是否截断: {'是' if text['is_truncated'] else '否'}",
                "",
                f"📄 **内容预览:**",
                text["text_content"][:500] + ("..." if len(text["text_content"]) > 500 else "")
            ])
        
        elif analysis_type == "links":
            links = result
            output.extend([
                f"🔗 **链接分析统计**",
                f"• 总链接数: {links['link_statistics']['total_links']}",
                f"• 内部链接: {links['link_statistics']['internal_links']}",
                f"• 外部链接: {links['link_statistics']['external_links']}",
                f"• 锚点链接: {links['link_statistics']['anchor_links']}",
                f"• 邮箱链接: {links['link_statistics']['email_links']}",
                ""
            ])
            
            if links["links"]:
                output.append("🎯 **主要链接:**")
                for i, link in enumerate(links["links"][:10], 1):
                    link_type = {"internal": "内部", "external": "外部", "anchor": "锚点", "email": "邮箱"}.get(link["type"], link["type"])
                    output.append(f"{i}. [{link['text'][:50]}]({link['url']}) ({link_type})")
        
        elif analysis_type == "metadata":
            meta = result
            output.extend([
                f"📋 **页面元数据**",
                f"• 标题: {meta['title']}",
                f"• 描述: {meta['description'][:200]}{'...' if len(meta['description']) > 200 else ''}",
                f"• 语言: {meta['language']}",
                f"• 关键词: {meta['keywords'][:100]}{'...' if len(meta['keywords']) > 100 else ''}",
                ""
            ])
            
            if meta["headings"]:
                output.append("📑 **页面结构 (标题):**")
                for h in meta["headings"][:10]:
                    indent = "  " * (h["level"] - 1)
                    output.append(f"{indent}H{h['level']}: {h['text'][:100]}")
        
        elif analysis_type in ["basic", "detailed"]:
            # Page info
            if "page_info" in result:
                info = result["page_info"]
                output.extend([
                    f"📊 **页面信息**",
                    f"• 状态码: {info['status_code']}",
                    f"• 内容类型: {info['content_type']}",
                    f"• 页面大小: {info['size_bytes']:,} bytes",
                    ""
                ])
            
            # Text summary
            if "text" in result:
                text = result["text"]
                output.extend([
                    f"📝 **文本内容**",
                    f"• 字符数: {text.get('character_count', 'N/A'):,}" if 'character_count' in text else f"• 字符数: {len(text.get('preview', ''))}/预览",
                    f"• 单词数: {text.get('word_count', 'N/A'):,}" if 'word_count' in text else "",
                    ""
                ])
            
            # Metadata
            if "metadata" in result:
                meta = result["metadata"]
                output.extend([
                    f"📋 **元数据**",
                    f"• 标题: {meta.get('title', 'N/A')}",
                    f"• 描述: {meta.get('description', 'N/A')[:100]}{'...' if len(meta.get('description', '')) > 100 else ''}",
                    ""
                ])
            
            # Links summary
            if "links" in result:
                links = result["links"]
                output.extend([
                    f"🔗 **链接统计**",
                    f"• 总链接: {links.get('total_links', 0)}",
                    f"• 外部链接: {links.get('external_links', 0)}",
                    ""
                ])
            
            # Additional detailed analysis
            if analysis_type == "detailed":
                if "images" in result:
                    images = result["images"]
                    output.extend([
                        f"🖼️ **图片统计**",
                        f"• 总图片数: {images['total_images']}",
                        ""
                    ])
                
                if "structure" in result:
                    struct = result["structure"]
                    output.extend([
                        f"🏗️ **页面结构**",
                        f"• 导航栏: {'有' if struct['has_navigation'] else '无'}",
                        f"• 页眉: {'有' if struct['has_header'] else '无'}",
                        f"• 页脚: {'有' if struct['has_footer'] else '无'}",
                        f"• 章节数: {struct['sections']}",
                        f"• 文章数: {struct['articles']}",
                        ""
                    ])
        
        return "\n".join(output)


def create_web_content_tools() -> List[BaseTool]:
    """Create web content analysis tools."""
    return [WebContentTool()]