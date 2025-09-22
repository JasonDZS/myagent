#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Call Logger Module

This module provides logging functionality for all large language model
interactions, recording inputs, outputs, and metadata for analysis and debugging.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from threading import Lock

from .logger import logger


class LLMCallLogger:
    """Logger for LLM API calls and responses.
    
    This class provides thread-safe logging of all interactions with large
    language models, including request/response pairs, token counts, and
    metadata for performance analysis and debugging.
    
    Attributes:
        log_file_path: Path to the JSON log file
    """
    
    def __init__(self, log_file_path: str = "workdir/llm_response.json"):
        """Initialize the LLM call logger.
        
        Args:
            log_file_path: Path to store the log file
        """
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for concurrent write safety
        self._lock = Lock()
        
        # Initialize log file
        self._initialize_log_file()
    
    def _initialize_log_file(self):
        """Initialize the log file if it doesn't exist."""
        if not self.log_file_path.exists():
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def log_llm_call(self, 
                     model: str,
                     messages: List[Dict[str, str]],
                     response: str,
                     metadata: Optional[Dict[str, Any]] = None):
        """Log an LLM API call.
        
        Args:
            model: The model name/identifier used
            messages: List of message dictionaries (request)
            response: The response text from the model
            metadata: Optional additional metadata
        """
        try:
            # Create call record
            call_record = {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "messages": messages,
                "response": response,
                "metadata": metadata or {},
                "token_count": {
                    "input_tokens": self._estimate_tokens(messages),
                    "output_tokens": self._estimate_tokens([{"content": response}])
                }
            }
            
            # Thread-safe file writing
            with self._lock:
                self._append_to_log_file(call_record)
                
            logger.debug(
                f"LLM call logged: {model}, "
                f"input {call_record['token_count']['input_tokens']} tokens, "
                f"output {call_record['token_count']['output_tokens']} tokens"
            )
            
        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}")
    
    def _append_to_log_file(self, record: Dict[str, Any]):
        """Append a record to the log file.
        
        Args:
            record: The log record to append
        """
        try:
            # Read existing records
            if self.log_file_path.exists():
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            else:
                existing_records = []
            
            # Add new record
            existing_records.append(record)
            
            # Write back to file
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_records, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to write to LLM log file: {e}")
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages.
        
        Simple estimation: English ~4 chars per token, Chinese ~1.5 chars per token.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Estimated token count
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)
        
        # Simple estimation: average 2.5 characters per token
        return int(total_chars / 2.5)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get call statistics.
        
        Returns:
            Dictionary containing usage statistics
        """
        try:
            if not self.log_file_path.exists():
                return {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "models_used": [],
                    "date_range": None
                }
            
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            if not records:
                return {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "models_used": [],
                    "date_range": None
                }
            
            # Calculate statistics
            total_calls = len(records)
            total_input_tokens = sum(r.get("token_count", {}).get("input_tokens", 0) for r in records)
            total_output_tokens = sum(r.get("token_count", {}).get("output_tokens", 0) for r in records)
            models_used = list(set(r.get("model", "unknown") for r in records))
            
            timestamps = [r.get("timestamp") for r in records if r.get("timestamp")]
            date_range = {
                "earliest": min(timestamps) if timestamps else None,
                "latest": max(timestamps) if timestamps else None
            }
            
            return {
                "total_calls": total_calls,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "models_used": models_used,
                "date_range": date_range
            }
            
        except Exception as e:
            logger.error(f"Failed to get LLM call statistics: {e}")
            return {
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "models_used": [],
                "date_range": None,
                "error": str(e)
            }
    
    def clear_logs(self):
        """Clear all log records."""
        try:
            with self._lock:
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logger.info("LLM call logs cleared")
        except Exception as e:
            logger.error(f"Failed to clear LLM logs: {e}")
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent call records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent call records, sorted by timestamp (newest first)
        """
        try:
            if not self.log_file_path.exists():
                return []
            
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            # Sort by timestamp and return recent records
            sorted_records = sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True)
            return sorted_records[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent LLM call records: {e}")
            return []


# Global singleton instance
_llm_call_logger = None

def get_llm_logger() -> LLMCallLogger:
    """Get the LLM call logger singleton instance.
    
    Returns:
        The global LLMCallLogger instance
    """
    global _llm_call_logger
    if _llm_call_logger is None:
        _llm_call_logger = LLMCallLogger()
    return _llm_call_logger