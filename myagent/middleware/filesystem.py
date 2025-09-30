#!/usr/bin/env python3
"""
Filesystem Middleware

Adds virtual file system capabilities to agents.
Provides file manipulation tools and file-specific prompts.
"""

from typing import List
from myagent.tool.base_tool import BaseTool
from myagent.tool.filesystem import get_filesystem_tools
from .base import BaseMiddleware, MiddlewareContext


class FilesystemMiddleware(BaseMiddleware):
    """
    Middleware that adds virtual file system capabilities to agents.
    
    Provides:
    - File system tools (ls, read_file, write_file, edit_file)
    - File management guidance
    - Virtual file persistence within session
    """
    
    name: str = "filesystem_middleware"
    description: str = "Adds virtual file system capabilities"
    priority: int = 20  # After planning, before sub-agents
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._filesystem_tools = get_filesystem_tools()
    
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        """Add filesystem tools and prompt to context."""
        
        # Add filesystem tools
        context.tools.extend(self._filesystem_tools)
        
        # Add filesystem guidance to system prompt
        filesystem_prompt = self.get_system_prompt_addition(context)
        if filesystem_prompt:
            context.system_prompt_parts.append(filesystem_prompt)
        
        # Add filesystem metadata
        context.metadata["has_filesystem"] = True
        context.metadata["filesystem_tools"] = [tool.name for tool in self._filesystem_tools]
        
        return context
    
    def get_tools(self) -> List[BaseTool]:
        """Return filesystem tools."""
        return self._filesystem_tools
    
    def get_system_prompt_addition(self, context: MiddlewareContext) -> str:
        """Return filesystem-specific system prompt."""
        return """## Virtual File System

You have access to a virtual file system that persists throughout your session:

**Available file operations:**
- `ls()` - List all files with sizes
- `read_file(file_path, line_offset=0, limit=2000)` - Read file content with line numbers
- `write_file(file_path, content)` - Write/overwrite file content
- `edit_file(file_path, old_string, new_string, replace_all=False)` - Edit specific content

**File management best practices:**
1. Use descriptive file names (e.g., "research_report.md", "analysis_results.txt")
2. Read files before editing to understand current content
3. Use line_offset and limit for large files
4. For edits, provide enough context to ensure unique string matches
5. Use replace_all=True only when you want to replace ALL occurrences

**File system features:**
- Files persist throughout the session
- Line numbers included in read output for easy reference
- Automatic size formatting and progress tracking
- Support for text files of any size
- Error handling for missing files or ambiguous edits

**Typical workflow:**
1. Use `ls` to see what files exist
2. Use `read_file` to examine content
3. Use `write_file` to create new documents
4. Use `edit_file` to make specific changes

The virtual file system enables complex workflows involving document creation, research compilation, and iterative content development."""
    
    async def pre_execution_hook(self, context: MiddlewareContext) -> None:
        """Log available files before execution."""
        from myagent.tool.filesystem import get_global_filesystem
        vfs = get_global_filesystem()
        files = vfs.list_files()
        context.metadata["initial_file_count"] = len(files)
    
    async def post_execution_hook(self, context: MiddlewareContext, result: str) -> str:
        """Log file changes after execution."""
        from myagent.tool.filesystem import get_global_filesystem
        vfs = get_global_filesystem()
        files = vfs.list_files()
        
        initial_count = context.metadata.get("initial_file_count", 0)
        final_count = len(files)
        
        if final_count != initial_count:
            file_change = f"\n\n📁 File System: {final_count} files ({final_count - initial_count:+d} change)"
            result += file_change
        
        return result