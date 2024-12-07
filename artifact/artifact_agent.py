from griptape.structures import Agent
from griptape.artifacts import TextArtifact
from typing import Optional, Any, Dict
import json
import re


class ArtifactAgent(Agent):
    """An Agent that handles artifact generation within conversational responses.

    This agent uses pattern recognition and content analysis to automatically detect
    and properly format different types of content as artifacts. It can handle various
    content types including code, React components, markdown, SVG, and more.
    """

    # Define content type patterns and their associated metadata
    CONTENT_PATTERNS = {
        # Code patterns for different languages
        "python": {
            "pattern": r"(def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import|print\()",
            "type": "code",
            "metadata": {"language": "python"},
        },
        "javascript": {
            "pattern": r"(function\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+|\=\>|module\.exports)",
            "type": "code",
            "metadata": {"language": "javascript"},
        },
        # React/JSX patterns
        "react": {
            "pattern": r'(<[\w]+[^>]*>|import\s+.*?from\s+[\'"]react[\'"]|const.*?\=.*?\(\s*\)\s*\=\>|function\s+\w+Component)',
            "type": "react",
            "metadata": {"framework": "react"},
        },
        # SVG patterns
        "svg": {
            "pattern": r"(<svg[^>]*>.*?</svg>)",
            "type": "svg",
            "metadata": {"format": "svg"},
        },
        # Markdown patterns
        "markdown": {
            "pattern": r"(^#{1,6}\s|\*\*.*?\*\*|__.*?__|```|\[.*?\]\(.*?\))",
            "type": "markdown",
            "metadata": {"format": "markdown"},
        },
        # Base64 patterns for binary content
        "base64_image": {
            "pattern": r'(data:image\/[^;]+;base64,([^"]+))',
            "type": "image",
            "metadata": {"encoding": "base64"},
        },
        "base64_audio": {
            "pattern": r'(data:audio\/[^;]+;base64,([^"]+))',
            "type": "audio",
            "metadata": {"encoding": "base64"},
        },
    }

    def wrap_artifact(
        self, artifact_type: str, content: Any, metadata: Optional[dict] = None
    ) -> str:
        """Creates a formatted artifact string with proper metadata and structure.

        Args:
            artifact_type: The type of artifact (e.g., "code", "react", "markdown")
            content: The content to be wrapped
            metadata: Additional metadata about the content

        Returns:
            A properly formatted artifact string with start/end tags
        """
        if not isinstance(content, str):
            content = str(content)

        artifact_data = {
            "type": artifact_type.lower().strip(),
            "content": content,
            "metadata": metadata or {},
        }

        return f"[ARTIFACT_START] {json.dumps(artifact_data, ensure_ascii=False)} [ARTIFACT_END]"

    def detect_content_type(self, content: str) -> Dict[str, Any]:
        """Analyzes content to determine its type and appropriate metadata.

        This method uses pattern matching and content analysis to identify the
        type of content and gather relevant metadata about it. It can handle
        multiple content types within the same text.

        Args:
            content: The content to analyze

        Returns:
            Dictionary containing content type and metadata
        """
        # First check for explicit code blocks
        code_block_match = re.search(r"```(\w+)?\n(.*?)\n```", content, re.DOTALL)
        if code_block_match:
            language = code_block_match.group(1) or "text"
            return {"type": "code", "metadata": {"language": language}}

        # Check against defined patterns
        for pattern_info in self.CONTENT_PATTERNS.values():
            if re.search(pattern_info["pattern"], content, re.MULTILINE | re.DOTALL):
                return {
                    "type": pattern_info["type"],
                    "metadata": pattern_info["metadata"],
                }

        # Default to plain text if no specific pattern matches
        return {"type": "text", "metadata": {"format": "plain"}}

    def process_content(self, content: str) -> str:
        """Processes content to properly format it as artifacts.

        This method handles both single and mixed content types, ensuring each
        distinct piece of content is properly wrapped as an artifact.

        Args:
            content: The content to process

        Returns:
            Processed content with appropriate artifact wrapping
        """
        # Handle explicit code blocks first
        if "```" in content:
            return self.process_code_blocks(content)

        # Detect content type and wrap appropriately
        content_info = self.detect_content_type(content)
        return self.wrap_artifact(
            content_info["type"], content, content_info["metadata"]
        )

    def try_run(self, *args) -> Agent:
        """Executes the agent's response generation with artifact support."""
        result = super().try_run(*args)

        if result.output_task and result.output_task.output:
            original_output = result.output_task.output.to_text()
            processed_output = self.process_content(original_output)
            result.output_task.output = TextArtifact(processed_output)

        return result

    def process_code_blocks(self, text: str) -> str:
        """Processes text containing code blocks into artifacts.

        This method handles markdown-style code blocks, converting them into
        properly formatted code artifacts while preserving surrounding context.

        Args:
            text: Text containing code blocks

        Returns:
            Processed text with code blocks converted to artifacts
        """
        parts = []
        current_pos = 0

        pattern = r"```(\w+)?\n(.*?)\n```"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            # Add text before code block
            parts.append(text[current_pos : match.start()])

            language = match.group(1) or "text"
            code_content = match.group(2).strip()

            # Create code artifact
            artifact = self.wrap_artifact("code", code_content, {"language": language})

            parts.append(artifact)
            current_pos = match.end()

        # Add remaining text
        parts.append(text[current_pos:])

        return "".join(parts)
