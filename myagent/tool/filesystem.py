#!/usr/bin/env python3
"""
Deep Agents Virtual File System

Implements a virtual file system similar to DeepAgents' file tools.
Provides ls, read_file, write_file, and edit_file capabilities for agent memory-based storage.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import os

from .base_tool import BaseTool, ToolResult


class VirtualFileSystem:
    """
    Virtual file system implementation using in-memory storage.
    
    Provides file operations that persist across agent execution within
    the same session, enabling complex workflows that require file state.
    """
    
    def __init__(self):
        self._files: Dict[str, str] = {}
    
    def list_files(self) -> Dict[str, int]:
        """List all files with their sizes."""
        return {path: len(content) for path, content in self._files.items()}
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        return file_path in self._files
    
    def read_file(self, file_path: str, line_offset: int = 0, limit: int = 2000) -> str:
        """Read file content with line number formatting."""
        if not self.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = self._files[file_path]
        lines = content.split('\n')
        
        # Apply offset and limit
        start = line_offset
        end = min(start + limit, len(lines))
        selected_lines = lines[start:end]
        
        # Format with line numbers (1-based)
        formatted_lines = []
        for i, line in enumerate(selected_lines, start + 1):
            # Truncate lines longer than 2000 characters
            if len(line) > 2000:
                line = line[:2000] + "..."
            formatted_lines.append(f"{i:4d}\t{line}")
        
        return '\n'.join(formatted_lines)
    
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file."""
        self._files[file_path] = content
    
    def edit_file(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """Edit file content by replacing strings."""
        if not self.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = self._files[file_path]
        
        # Check for matches
        occurrences = content.count(old_string)
        if occurrences == 0:
            raise ValueError(f"String not found: '{old_string}'")
        
        if not replace_all and occurrences > 1:
            raise ValueError(
                f"Multiple matches found ({occurrences}). "
                "Provide more specific context or use replace_all=True"
            )
        
        # Perform replacement
        if replace_all:
            updated_content = content.replace(old_string, new_string)
        else:
            updated_content = content.replace(old_string, new_string, 1)
        
        self._files[file_path] = updated_content
        return f"Replaced {1 if not replace_all else occurrences} occurrence(s)"


# Global file system instance for persistence across tool calls
_global_vfs = VirtualFileSystem()


class ListFilesTool(BaseTool):
    """Tool for listing files in the virtual file system."""
    
    name: str = "ls"
    description: str = "List all files in the virtual file system with their sizes"
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, **kwargs) -> ToolResult:
        """List all files in the virtual file system."""
        try:
            files = _global_vfs.list_files()
            
            if not files:
                return ToolResult(output="📁 Virtual file system is empty")
            
            # Format file listing
            output_lines = ["📁 **Virtual File System Contents:**", ""]
            
            # Sort files by name for consistent output
            sorted_files = sorted(files.items())
            
            for file_path, size in sorted_files:
                # Format file size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                
                output_lines.append(f"📄 {file_path} ({size_str})")
            
            output_lines.append(f"\n📊 Total: {len(files)} file(s)")
            
            return ToolResult(output="\n".join(output_lines))
            
        except Exception as e:
            return ToolResult(error=f"Failed to list files: {str(e)}")


class ReadFileTool(BaseTool):
    """Tool for reading files from the virtual file system."""
    
    name: str = "read_file"
    description: str = "Read content from a file in the virtual file system with optional line range"
    parameters: dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read"
            },
            "line_offset": {
                "type": "integer",
                "description": "Starting line number (0-based)",
                "default": 0
            },
            "limit": {
                "type": "integer", 
                "description": "Maximum number of lines to read",
                "default": 2000
            }
        },
        "required": ["file_path"]
    }

    async def execute(self, file_path: str, line_offset: int = 0, limit: int = 2000, **kwargs) -> ToolResult:
        """Read file content with line numbers."""
        try:
            content = _global_vfs.read_file(file_path, line_offset, limit)
            
            # Add file header
            file_info = f"📄 **File: {file_path}**"
            if line_offset > 0 or limit < 2000:
                file_info += f" (lines {line_offset + 1}-{line_offset + len(content.split(chr(10)))})"
            
            output = f"{file_info}\n\n{content}"
            
            return ToolResult(output=output)
            
        except FileNotFoundError as e:
            return ToolResult(error=str(e))
        except Exception as e:
            return ToolResult(error=f"Failed to read file: {str(e)}")


class WriteFileTool(BaseTool):
    """Tool for writing files to the virtual file system."""
    
    name: str = "write_file"
    description: str = "Write content to a file in the virtual file system (overwrites existing content)"
    parameters: dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["file_path", "content"]
    }

    async def execute(self, file_path: str, content: str, **kwargs) -> ToolResult:
        """Write content to a file."""
        try:
            was_existing = _global_vfs.file_exists(file_path)
            _global_vfs.write_file(file_path, content)
            
            # Format size
            size = len(content)
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            action = "Updated" if was_existing else "Created"
            output = f"✅ {action} file: {file_path} ({size_str})"
            
            return ToolResult(
                output=output,
                system=f"File {file_path} written successfully"
            )
            
        except Exception as e:
            return ToolResult(error=f"Failed to write file: {str(e)}")


class EditFileTool(BaseTool):
    """Tool for editing files in the virtual file system."""
    
    name: str = "edit_file"
    description: str = "Edit a file by replacing specific text content"
    parameters: dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "old_string": {
                "type": "string",
                "description": "Text to find and replace"
            },
            "new_string": {
                "type": "string",
                "description": "Replacement text"
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (default: false, requires unique match)",
                "default": False
            }
        },
        "required": ["file_path", "old_string", "new_string"]
    }

    async def execute(
        self, 
        file_path: str, 
        old_string: str, 
        new_string: str, 
        replace_all: bool = False,
        **kwargs
    ) -> ToolResult:
        """Edit file by replacing text."""
        try:
            result_msg = _global_vfs.edit_file(file_path, old_string, new_string, replace_all)
            
            # Create preview of change
            preview_old = old_string[:50] + "..." if len(old_string) > 50 else old_string
            preview_new = new_string[:50] + "..." if len(new_string) > 50 else new_string
            
            output = [
                f"✅ **File Edit Successful: {file_path}**",
                "",
                f"📝 **Change:** {result_msg}",
                f"🔍 **From:** `{preview_old}`",
                f"🔄 **To:** `{preview_new}`"
            ]
            
            return ToolResult(
                output="\n".join(output),
                system=f"File {file_path} edited successfully"
            )
            
        except FileNotFoundError as e:
            return ToolResult(error=str(e))
        except ValueError as e:
            return ToolResult(error=str(e))
        except Exception as e:
            return ToolResult(error=f"Failed to edit file: {str(e)}")


def get_filesystem_tools() -> list[BaseTool]:
    """Get all virtual file system tools."""
    return [
        ListFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool()
    ]


def get_global_filesystem() -> VirtualFileSystem:
    """Get the global virtual file system instance."""
    return _global_vfs


def clear_filesystem() -> None:
    """Clear all files from the virtual file system."""
    global _global_vfs
    _global_vfs = VirtualFileSystem()