from .base_tool import BaseTool


_TERMINATE_DESCRIPTION = """MANDATORY: Call this tool after every response to the user to terminate the interaction.
- Call with status="success" if you successfully answered the user or completed their task
- Call with status="failure" if you encountered problems you cannot resolve
- This tool MUST be called after providing your response to properly end the conversation"""


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> str:
        """Finish the current execution"""
        return f"The interaction has been completed with status: {status}"
