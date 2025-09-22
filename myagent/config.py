import os
from typing import Any, ClassVar, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(".env")

class LLMSettings(BaseModel):
    model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-3.5-turbo"))
    base_url: str = Field(default_factory=lambda: os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    max_tokens: int = Field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2048")),
        description="Maximum number of tokens per request"
    )
    max_input_tokens: Optional[int] = Field(None, description="Maximum number of input tokens for the model")
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field("Openai", description="Azure, Openai, or Ollama")
    api_version: str = Field("v1", description="Azure Openai version if AzureOpenai")



class Settings(BaseModel):
    _instance: ClassVar[Optional["Settings"]] = None

    workdir: str = Field(default="workdir/finance", description="Base working directory")
    retrieval_workdir: str = Field(default="workdir/finance")
    template: str = Field(default="workdir/template/产品需求评审会议.md")

    # OpenAI settings
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_API_BASE: str = Field(default_factory=lambda: os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))

    # Model settings
    llm_settings: LLMSettings = Field(
        default_factory=LLMSettings,
        description="Settings for the language model including model name, API key, and other parameters"
    )

    # Embedding settings
    EMBEDDING_MODEL: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "Pro/BAAI/bge-m3"))
    EMBEDDING_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "openai")
    )  # Options: "openai", "hf", "ollama"
    EMBEDDING_DIM: int = Field(
        default_factory=lambda: int(os.getenv("EMBEDDING_DIM", "1024"))
    )  # Default dimension for BGE models
    EMBEDDING_MAX_TOKEN_SIZE: int = Field(
        default_factory=lambda: int(os.getenv("EMBEDDING_MAX_TOKENS", "8192"))
    )  # Default max token size for BGE models

    # Markdown Conversion settings
    MARKDOWN_PRESERVE_HTML: bool = Field(
        default_factory=lambda: os.getenv("MARKDOWN_PRESERVE_HTML", "true").lower() == "true"
    )
    MARKDOWN_INCLUDE_METADATA: bool = Field(
        default_factory=lambda: os.getenv("MARKDOWN_INCLUDE_METADATA", "true").lower() == "true"
    )
    MARKDOWN_FLATTEN_STRUCTURE: bool = Field(
        default_factory=lambda: os.getenv("MARKDOWN_FLATTEN_STRUCTURE", "false").lower() == "true"
    )
    MARKDOWN_MAX_DEPTH: int = Field(
        default_factory=lambda: int(os.getenv("MARKDOWN_MAX_DEPTH", "10"))
    )
    MARKDOWN_OUTPUT_FORMAT: str = Field(
        default_factory=lambda: os.getenv("MARKDOWN_OUTPUT_FORMAT", "json")
    )  # Options: "json", "yaml", "xml"
    
    # Knowledge Retrieval settings
    distance: float = Field(default = 1.5, description = "Distance threshold for embedding similarity")
    top_k: int = Field(default = 5, description = "Number of top results to return from embedding search")
    chunk_size: int = Field(default = 1200, description = "")
    chunk_overlap: int = Field(default = 240, description = "")
    sentence_level: bool = Field(
        default=True,
        description="Use sentence level filtering or not"
    )
    max_retrieval_length: int = Field(default = 400, description = "")
    top_k_sentences: int = Field(default = 6, description = "")
    lambda_mmr: float = Field(default = 0.6, description = "")
    overlap_window: int = Field(default = 1, description = "")
    
    parallel_sections: bool = Field(default = False, description = "Whether to process sections in parallel")
    max_concurrent: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT", "4")),
        description="Maximum number of concurrent sections to process"
    )
    section_agent_react: bool = Field(
        default=True,
        description="Whether to use ReAct agent for section processing"
    )
    use_agraph: bool = Field(
        default=False,
        description="Whether to use AGraph for knowledge retrieval"
    )

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if not hasattr(cls, "_instance") or cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if hasattr(self, "_initialized"):
            return
        super().__init__(*args, **kwargs)
        self._initialized = True

    class Config:
        arbitrary_types_allowed = True


# Create singleton instance
settings = Settings()
