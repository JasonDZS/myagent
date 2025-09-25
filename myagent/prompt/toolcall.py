#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Call Agent Prompt Templates

This module contains prompt templates for agents that can execute tool calls.
It provides basic system prompts and instructions for tool-based interactions.
"""

# System prompt for tool call agents
SYSTEM_PROMPT = "You are an agent that can execute tool calls"

# Next step prompt for guiding tool call workflow
NEXT_STEP_PROMPT = (
    "If you want to stop interaction, use `terminate` tool/function call."
)

# Summary prompt for final step after special tool execution
SUMMARY_PROMPT = (
    "Please provide a comprehensive summary of the entire conversation and task execution. "
    "Include: 1) The original task/request, 2) Key steps taken and tools used, "
    "3) Important findings or results, 4) Final outcome. "
    "Make the summary clear and concise for easy understanding."
)
