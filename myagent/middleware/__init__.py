#!/usr/bin/env python3
"""
Deep Agents Middleware System

Middleware system for extending agent capabilities through composable middleware layers.
Inspired by DeepAgents' middleware architecture but adapted for myagent's framework.
"""

from .base import BaseMiddleware, MiddlewareContext
from .planning import PlanningMiddleware
from .filesystem import FilesystemMiddleware  
from .subagent import SubAgentMiddleware
from .deep_agent import DeepAgentMiddleware

__all__ = [
    "BaseMiddleware",
    "MiddlewareContext", 
    "PlanningMiddleware",
    "FilesystemMiddleware",
    "SubAgentMiddleware",
    "DeepAgentMiddleware"
]