#!/usr/bin/env python3
"""
Academic Search Tool

Integrates with arXiv API and other academic databases for scholarly research.
Provides access to scientific papers, preprints, and academic publications.
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from .base_tool import BaseTool, ToolResult


class ArxivPaper(BaseModel):
    """arXiv paper model."""
    
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(..., description="List of authors")
    abstract: str = Field(..., description="Paper abstract")
    arxiv_id: str = Field(..., description="arXiv ID")
    pdf_url: str = Field(..., description="PDF URL")
    published: datetime = Field(..., description="Publication date")
    categories: List[str] = Field(default_factory=list, description="Subject categories")
    
    
class ArxivSearchTool(BaseTool):
    """
    Real arXiv search tool for academic research.
    
    Searches arXiv database for scientific papers and preprints.
    """
    
    name: str = "arxiv_search"
    description: str = "Search arXiv database for academic papers and preprints"
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for papers (title, abstract, author, or keywords)"
            },
            "category": {
                "type": "string",
                "description": "arXiv category (e.g., 'cs.AI', 'cs.CL', 'stat.ML', 'physics')",
                "default": "all"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of papers to return",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            },
            "sort_by": {
                "type": "string",
                "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                "description": "Sort order for results",
                "default": "relevance"
            },
            "date_range": {
                "type": "string",
                "description": "Date range filter (e.g., 'last_year', 'last_month', '2023', '2022-2024')",
                "default": "all"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._base_url = "http://export.arxiv.org/api/query"
        
        # arXiv category mapping
        self._categories = {
            "ai": "cs.AI",
            "cl": "cs.CL", 
            "ml": "cs.LG",
            "cv": "cs.CV",
            "nlp": "cs.CL",
            "robotics": "cs.RO",
            "crypto": "cs.CR",
            "systems": "cs.SY",
            "math": "math",
            "physics": "physics",
            "statistics": "stat.ML",
            "biology": "q-bio",
            "finance": "q-fin"
        }
    
    async def execute(
        self,
        query: str,
        category: str = "all",
        max_results: int = 10,
        sort_by: str = "relevance",
        date_range: str = "all",
        **kwargs
    ) -> ToolResult:
        """
        Search arXiv database for papers.
        
        Args:
            query: Search query
            category: arXiv category filter
            max_results: Maximum results to return
            sort_by: Sort order
            date_range: Date range filter
            
        Returns:
            ToolResult with paper search results
        """
        try:
            # Build search query
            search_query = self._build_arxiv_query(query, category, date_range)
            
            # Prepare parameters
            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": min(max_results, 100),
                "sortBy": sort_by,
                "sortOrder": "descending"
            }
            
            # Execute search
            async with aiohttp.ClientSession() as session:
                async with session.get(self._base_url, params=params) as response:
                    if response.status != 200:
                        return ToolResult(
                            error=f"arXiv API error ({response.status}): {await response.text()}"
                        )
                    
                    xml_content = await response.text()
            
            # Parse XML response
            papers = self._parse_arxiv_response(xml_content)
            
            if not papers:
                return ToolResult(
                    output=f"🎓 **arXiv 搜索结果 - {query}**\n\n未找到相关论文。",
                    system=f"No papers found on arXiv for: {query}"
                )
            
            # Format output
            output = self._format_arxiv_results(query, category, papers)
            
            return ToolResult(
                output=output,
                system=f"Found {len(papers)} papers on arXiv for '{query}'"
            )
            
        except Exception as e:
            return ToolResult(error=f"arXiv search failed: {str(e)}")
    
    def _build_arxiv_query(self, query: str, category: str, date_range: str) -> str:
        """Build arXiv API query string."""
        
        # Clean and prepare query
        search_terms = []
        
        # Add main query
        if query:
            # Search in title, abstract, and authors
            search_terms.append(f"(ti:\"{query}\" OR abs:\"{query}\" OR au:\"{query}\")")
        
        # Add category filter
        if category != "all":
            # Map common names to arXiv categories
            arxiv_category = self._categories.get(category.lower(), category)
            search_terms.append(f"cat:{arxiv_category}")
        
        # Add date range filter
        if date_range != "all":
            date_filter = self._build_date_filter(date_range)
            if date_filter:
                search_terms.append(date_filter)
        
        return " AND ".join(search_terms)
    
    def _build_date_filter(self, date_range: str) -> Optional[str]:
        """Build date filter for arXiv query."""
        
        try:
            now = datetime.now()
            
            if date_range == "last_year":
                start_date = now - timedelta(days=365)
                return f"submittedDate:[{start_date.strftime('%Y%m%d')}* TO *]"
            elif date_range == "last_month":
                start_date = now - timedelta(days=30)
                return f"submittedDate:[{start_date.strftime('%Y%m%d')}* TO *]"
            elif date_range == "last_week":
                start_date = now - timedelta(days=7)
                return f"submittedDate:[{start_date.strftime('%Y%m%d')}* TO *]"
            elif date_range.isdigit() and len(date_range) == 4:  # Single year
                return f"submittedDate:[{date_range}* TO {date_range}*]"
            elif "-" in date_range and len(date_range.split("-")) == 2:  # Year range
                start_year, end_year = date_range.split("-")
                if start_year.isdigit() and end_year.isdigit():
                    return f"submittedDate:[{start_year}* TO {end_year}*]"
                    
        except Exception:
            pass
        
        return None
    
    def _parse_arxiv_response(self, xml_content: str) -> List[ArxivPaper]:
        """Parse arXiv XML response into paper objects."""
        
        papers = []
        
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Find all entry elements (papers)
            namespace = {"atom": "http://www.w3.org/2005/Atom", 
                        "arxiv": "http://arxiv.org/schemas/atom"}
            
            entries = root.findall("atom:entry", namespace)
            
            for entry in entries:
                try:
                    # Extract paper information
                    title = entry.find("atom:title", namespace)
                    title_text = title.text.strip().replace("\n", " ") if title is not None else "No title"
                    
                    # Authors
                    authors = []
                    for author in entry.findall("atom:author", namespace):
                        name = author.find("atom:name", namespace)
                        if name is not None:
                            authors.append(name.text.strip())
                    
                    # Abstract
                    summary = entry.find("atom:summary", namespace)
                    abstract = summary.text.strip().replace("\n", " ") if summary is not None else "No abstract"
                    
                    # arXiv ID and URL
                    id_elem = entry.find("atom:id", namespace)
                    arxiv_url = id_elem.text.strip() if id_elem is not None else ""
                    arxiv_id = arxiv_url.split("/")[-1] if "/" in arxiv_url else ""
                    
                    # PDF URL
                    pdf_url = ""
                    for link in entry.findall("atom:link", namespace):
                        if link.get("type") == "application/pdf":
                            pdf_url = link.get("href", "")
                            break
                    
                    # Published date
                    published_elem = entry.find("atom:published", namespace)
                    published_date = datetime.now()
                    if published_elem is not None:
                        try:
                            published_date = datetime.fromisoformat(published_elem.text.replace("Z", "+00:00"))
                        except:
                            pass
                    
                    # Categories
                    categories = []
                    for category in entry.findall("atom:category", namespace):
                        term = category.get("term")
                        if term:
                            categories.append(term)
                    
                    paper = ArxivPaper(
                        title=title_text,
                        authors=authors,
                        abstract=abstract,
                        arxiv_id=arxiv_id,
                        pdf_url=pdf_url,
                        published=published_date,
                        categories=categories
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    # Skip malformed entries
                    continue
                    
        except ET.ParseError as e:
            raise Exception(f"Failed to parse arXiv XML response: {str(e)}")
        
        return papers
    
    def _format_arxiv_results(self, query: str, category: str, papers: List[ArxivPaper]) -> str:
        """Format arXiv search results for display."""
        
        output = [
            f"🎓 **arXiv 搜索结果 - {query}**",
            f"📚 类别: {category}",
            f"📊 找到 {len(papers)} 篇论文",
            ""
        ]
        
        for i, paper in enumerate(papers, 1):
            # Format authors
            if len(paper.authors) > 3:
                authors_str = ", ".join(paper.authors[:3]) + " et al."
            else:
                authors_str = ", ".join(paper.authors)
            
            # Format categories
            categories_str = ", ".join(paper.categories[:3])
            
            # Format date
            date_str = paper.published.strftime("%Y-%m-%d")
            
            output.extend([
                f"**{i}. {paper.title}**",
                f"👨‍🎓 作者: {authors_str}",
                f"📅 发布时间: {date_str} | 📂 分类: {categories_str}",
                f"🆔 arXiv ID: {paper.arxiv_id}",
                f"🔗 [PDF链接]({paper.pdf_url})",
                f"📝 {paper.abstract[:300]}{'...' if len(paper.abstract) > 300 else ''}",
                ""
            ])
        
        return "\n".join(output)


class PubMedSearchTool(BaseTool):
    """
    PubMed search tool for medical and life sciences literature.
    
    Uses NCBI E-utilities API to search biomedical literature.
    """
    
    name: str = "pubmed_search"
    description: str = "Search PubMed database for biomedical and life sciences literature"
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for biomedical papers"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of papers to return",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            },
            "publication_type": {
                "type": "string",
                "enum": ["all", "review", "clinical_trial", "meta_analysis", "randomized_controlled_trial"],
                "description": "Type of publication to search for",
                "default": "all"
            },
            "date_range": {
                "type": "string",
                "description": "Publication date range (e.g., 'last_year', '2020-2024')",
                "default": "last_5_years"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    async def execute(
        self,
        query: str,
        max_results: int = 10,
        publication_type: str = "all",
        date_range: str = "last_5_years",
        **kwargs
    ) -> ToolResult:
        """Search PubMed database."""
        
        try:
            # Build PubMed query
            search_query = self._build_pubmed_query(query, publication_type, date_range)
            
            # Search PubMed
            search_params = {
                "db": "pubmed",
                "term": search_query,
                "retmax": min(max_results, 50),
                "retmode": "xml",
                "sort": "relevance"
            }
            
            async with aiohttp.ClientSession() as session:
                # First, get the list of PMIDs
                search_url = f"{self._base_url}/esearch.fcgi"
                async with session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        return ToolResult(
                            error=f"PubMed search API error ({response.status})"
                        )
                    
                    search_xml = await response.text()
                
                # Parse PMIDs from search results
                pmids = self._extract_pmids(search_xml)
                
                if not pmids:
                    return ToolResult(
                        output=f"🧬 **PubMed 搜索结果 - {query}**\n\n未找到相关文献。",
                        system=f"No PubMed articles found for: {query}"
                    )
                
                # Fetch detailed information for each PMID
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids[:max_results]),
                    "retmode": "xml"
                }
                
                fetch_url = f"{self._base_url}/efetch.fcgi"
                async with session.get(fetch_url, params=fetch_params) as response:
                    if response.status != 200:
                        return ToolResult(
                            error=f"PubMed fetch API error ({response.status})"
                        )
                    
                    articles_xml = await response.text()
                
                # Parse article details
                articles = self._parse_pubmed_articles(articles_xml)
                
                # Format output
                output = self._format_pubmed_results(query, publication_type, articles)
                
                return ToolResult(
                    output=output,
                    system=f"Found {len(articles)} PubMed articles for '{query}'"
                )
                
        except Exception as e:
            return ToolResult(error=f"PubMed search failed: {str(e)}")
    
    def _build_pubmed_query(self, query: str, publication_type: str, date_range: str) -> str:
        """Build PubMed search query."""
        
        query_parts = [query]
        
        # Add publication type filter
        if publication_type != "all":
            type_mapping = {
                "review": "Review[Publication Type]",
                "clinical_trial": "Clinical Trial[Publication Type]",
                "meta_analysis": "Meta-Analysis[Publication Type]",
                "randomized_controlled_trial": "Randomized Controlled Trial[Publication Type]"
            }
            if publication_type in type_mapping:
                query_parts.append(type_mapping[publication_type])
        
        # Add date range
        if date_range != "all":
            if date_range == "last_year":
                query_parts.append("1 year[PDat]")
            elif date_range == "last_5_years":
                query_parts.append("5 years[PDat]")
            elif "-" in date_range:
                try:
                    start_year, end_year = date_range.split("-")
                    query_parts.append(f"{start_year}:{end_year}[PDat]")
                except:
                    pass
        
        return " AND ".join(query_parts)
    
    def _extract_pmids(self, xml_content: str) -> List[str]:
        """Extract PMIDs from PubMed search response."""
        
        try:
            root = ET.fromstring(xml_content)
            pmids = []
            
            for id_elem in root.findall(".//Id"):
                pmids.append(id_elem.text)
                
            return pmids
        except:
            return []
    
    def _parse_pubmed_articles(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse PubMed article details from XML."""
        
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article_elem in root.findall(".//PubmedArticle"):
                try:
                    # Extract article information
                    citation = article_elem.find(".//MedlineCitation")
                    if citation is None:
                        continue
                    
                    # PMID
                    pmid_elem = citation.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
                    # Title
                    title_elem = citation.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else "No title"
                    
                    # Authors
                    authors = []
                    for author in citation.findall(".//Author"):
                        last_name = author.find("LastName")
                        first_name = author.find("ForeName")
                        if last_name is not None:
                            author_name = last_name.text
                            if first_name is not None:
                                author_name += f", {first_name.text}"
                            authors.append(author_name)
                    
                    # Abstract
                    abstract_elem = citation.find(".//Abstract/AbstractText")
                    abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
                    
                    # Journal
                    journal_elem = citation.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else "Unknown journal"
                    
                    # Publication date
                    pub_date = citation.find(".//PubDate")
                    year = pub_date.find("Year").text if pub_date is not None and pub_date.find("Year") is not None else ""
                    
                    article = {
                        "pmid": pmid,
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "journal": journal,
                        "year": year,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    }
                    
                    articles.append(article)
                    
                except Exception:
                    continue
                    
        except ET.ParseError:
            pass
        
        return articles
    
    def _format_pubmed_results(self, query: str, publication_type: str, articles: List[Dict[str, Any]]) -> str:
        """Format PubMed search results."""
        
        output = [
            f"🧬 **PubMed 搜索结果 - {query}**",
            f"📚 文献类型: {publication_type}",
            f"📊 找到 {len(articles)} 篇文献",
            ""
        ]
        
        for i, article in enumerate(articles, 1):
            authors_str = ", ".join(article["authors"][:3])
            if len(article["authors"]) > 3:
                authors_str += " et al."
            
            output.extend([
                f"**{i}. {article['title']}**",
                f"👨‍🎓 作者: {authors_str}",
                f"📰 期刊: {article['journal']} ({article['year']})",
                f"🆔 PMID: {article['pmid']}",
                f"🔗 {article['url']}",
                f"📝 {article['abstract'][:300]}{'...' if len(article['abstract']) > 300 else ''}",
                ""
            ])
        
        return "\n".join(output)


def create_academic_tools() -> List[BaseTool]:
    """Create all academic search tools."""
    return [
        ArxivSearchTool(),
        PubMedSearchTool()
    ]