from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class ElementType(str, Enum):
    """Enumeration of Markdown element types."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    LIST = "list"
    LIST_ITEM = "list_item"
    BLOCKQUOTE = "blockquote"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    LINK = "link"
    IMAGE = "image"
    BOLD = "bold"
    ITALIC = "italic"
    STRIKETHROUGH = "strikethrough"
    HORIZONTAL_RULE = "horizontal_rule"
    LINE_BREAK = "line_break"
    TEXT = "text"


class ListType(str, Enum):
    """Enumeration of list types."""

    ORDERED = "ordered"
    UNORDERED = "unordered"


class TableAlignment(str, Enum):
    """Enumeration of table alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    NONE = "none"


class MarkdownElement(BaseModel):
    """Base model for Markdown elements.

    This is the foundational class for all Markdown elements, providing
    common attributes and structure for element hierarchy.

    Attributes:
        type: The type of the Markdown element
        content: Optional text content of the element
        children: Optional list of child elements for nested structures
        attributes: Optional dictionary of element-specific attributes
    """

    type: ElementType = Field(..., description="Element type")
    content: str | None = Field(None, description="Text content")
    children: list["MarkdownElement"] | None = Field(
        None, description="List of child elements"
    )
    attributes: dict[str, Any] | None = Field(None, description="Element attributes")

    class Config:
        # Allow recursive model
        from_attributes = True


class HeadingElement(MarkdownElement):
    """Markdown heading element.

    Represents heading elements (h1-h6) with a specific level.

    Attributes:
        level: Heading level from 1 to 6
    """

    type: Literal[ElementType.HEADING] = Field(ElementType.HEADING)
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")

    def __init__(self, **data):
        super().__init__(**data)
        if self.attributes is None:
            self.attributes = {}
        self.attributes["level"] = self.level


class CodeBlockElement(MarkdownElement):
    """Code block element.

    Represents fenced code blocks with optional language specification.

    Attributes:
        language: Optional programming language for syntax highlighting
    """

    type: Literal[ElementType.CODE_BLOCK] = Field(ElementType.CODE_BLOCK)
    language: str | None = Field(None, description="Programming language")

    def __init__(self, **data):
        super().__init__(**data)
        if self.attributes is None:
            self.attributes = {}
        if self.language:
            self.attributes["language"] = self.language


class ListElement(MarkdownElement):
    """List element.

    Represents both ordered and unordered lists.

    Attributes:
        list_type: Type of list (ordered or unordered)
        start: Starting number for ordered lists
    """

    type: Literal[ElementType.LIST] = Field(ElementType.LIST)
    list_type: ListType = Field(..., description="List type")
    start: int | None = Field(None, description="Starting number for ordered lists")

    def __init__(self, **data):
        super().__init__(**data)
        if self.attributes is None:
            self.attributes = {}
        self.attributes["list_type"] = self.list_type
        if self.start is not None:
            self.attributes["start"] = self.start


class LinkElement(MarkdownElement):
    """Link element.

    Represents hyperlinks with URL and optional title.

    Attributes:
        url: The target URL
        title: Optional link title
    """

    type: Literal[ElementType.LINK] = Field(ElementType.LINK)
    url: str = Field(..., description="Link URL")
    title: str | None = Field(None, description="Link title")

    def __init__(self, **data):
        super().__init__(**data)
        if self.attributes is None:
            self.attributes = {}
        self.attributes["url"] = self.url
        if self.title:
            self.attributes["title"] = self.title


class ImageElement(MarkdownElement):
    """Image element.

    Represents embedded images with source URL and optional metadata.

    Attributes:
        src: Image source URL
        alt: Alternative text for accessibility
        title: Optional image title
    """

    type: Literal[ElementType.IMAGE] = Field(ElementType.IMAGE)
    src: str = Field(..., description="Image source URL")
    alt: str | None = Field(None, description="Alternative text")
    title: str | None = Field(None, description="Image title")

    def __init__(self, **data):
        super().__init__(**data)
        if self.attributes is None:
            self.attributes = {}
        self.attributes["src"] = self.src
        if self.alt:
            self.attributes["alt"] = self.alt
        if self.title:
            self.attributes["title"] = self.title


class TableElement(MarkdownElement):
    """Table element.

    Represents Markdown tables with headers and column alignments.

    Attributes:
        headers: List of table header labels
        alignments: List of column alignment specifications
    """

    type: Literal[ElementType.TABLE] = Field(ElementType.TABLE)
    headers: list[str] = Field(default_factory=list, description="Table headers")
    alignments: list[TableAlignment] = Field(
        default_factory=list, description="Column alignment options"
    )

    def __init__(self, **data):
        super().__init__(**data)
        if self.attributes is None:
            self.attributes = {}
        if self.headers:
            self.attributes["headers"] = self.headers
        if self.alignments:
            self.attributes["alignments"] = [align.value for align in self.alignments]


class MarkdownDocument(BaseModel):
    """Markdown document model.

    Represents a complete Markdown document with optional metadata.

    Attributes:
        title: Optional document title
        metadata: Optional document metadata dictionary
        content: List of document content elements
    """

    title: str | None = Field(None, description="Document title")
    metadata: dict[str, Any] | None = Field(None, description="Document metadata")
    content: list[MarkdownElement] = Field(
        default_factory=list, description="Document content element list"
    )

    class Config:
        from_attributes = True


class ConversionOptions(BaseModel):
    """Configuration options for conversion operations.

    Attributes:
        preserve_html: Whether to preserve HTML tags during conversion
        include_metadata: Whether to include metadata in the output
        flatten_structure: Whether to flatten the hierarchical structure
        custom_renderers: Optional custom renderer configurations
    """

    preserve_html: bool = Field(True, description="Whether to preserve HTML tags")
    include_metadata: bool = Field(True, description="Whether to include metadata")
    flatten_structure: bool = Field(False, description="Whether to flatten structure")
    custom_renderers: dict[str, str] | None = Field(
        None, description="Custom renderers"
    )


class ConversionRequest(BaseModel):
    """Request model for format conversion operations.

    Attributes:
        source_format: Source format identifier (markdown/json)
        target_format: Target format identifier (json/markdown)
        content: Content to be converted
        options: Optional conversion configuration
    """

    source_format: str = Field(..., description="Source format (markdown/json)")
    target_format: str = Field(..., description="Target format (json/markdown)")
    content: str | dict[str, Any] = Field(..., description="Content to convert")
    options: ConversionOptions | None = Field(None, description="Conversion options")


class ConversionResponse(BaseModel):
    """Response model for conversion operations.

    Attributes:
        success: Whether the conversion was successful
        result: The converted content (if successful)
        error: Error message (if conversion failed)
        metadata: Optional conversion metadata
    """

    success: bool = Field(..., description="Whether conversion was successful")
    result: str | dict[str, Any] | None = Field(None, description="Conversion result")
    error: str | None = Field(None, description="Error message")
    metadata: dict[str, Any] | None = Field(None, description="Conversion metadata")


# Update recursive model references
MarkdownElement.model_rebuild()
