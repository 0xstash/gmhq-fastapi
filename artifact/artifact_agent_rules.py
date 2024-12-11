from griptape.structures import Agent
from griptape.artifacts import TextArtifact
from griptape.rules import Rule, Ruleset
from typing import Optional, Any, Dict
import json
import re


class ArtifactAgent(Agent):
    """An Agent that intelligently handles artifact generation within responses.

    Uses rules-based decision making to determine when content should be an artifact,
    and handles appropriate formatting for different types of content.
    """

    # Define content type patterns for when we know we need to format specific content
    CONTENT_PATTERNS = {
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
        "react": {
            "pattern": r'(<[\w]+[^>]*>|import\s+.*?from\s+[\'"]react[\'"]|const.*?\=.*?\(\s*\)\s*\=\>|function\s+\w+Component)',
            "type": "react",
            "metadata": {"framework": "react"},
        },
        "svg": {
            "pattern": r"(<svg[^>]*>.*?</svg>)",
            "type": "svg",
            "metadata": {"format": "svg"},
        },
        "markdown": {
            "pattern": r"(^#{1,6}\s|\*\*.*?\*\*|__.*?__|```|\[.*?\]\(.*?\))",
            "type": "markdown",
            "metadata": {"format": "markdown"},
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add rules for artifact creation decisions
        artifact_rules = Ruleset(
            rules=[
                Rule(
                    """When responding, follow these guidelines for artifact creation:

                1. Create code artifacts when:
                   - Writing programming code in any language
                   - Showing configuration files
                   - Displaying command line instructions

                2. Create document artifacts when:
                   - Writing substantial creative content (stories, poems, scripts)
                   - Creating long-form analytical content
                   - Generating technical documentation
                   - Writing content meant to be used as reference material
                   
                3. DO NOT create artifacts for:
                   - Simple conversational responses
                   - Brief explanations
                   - Lists or short answers
                   - Basic questions and responses
                   
                4. If you create an artifact, ensure it follows these rules:
                   - Must be longer than 20 lines
                   - Must be content that benefits from special formatting or structure
                   - Must be content likely to be reused or referenced later
                   
                5. For all other responses, provide them directly without artifact formatting.

                6. When you decide to create an artifact, prefix your response with [NEEDS_ARTIFACT] 
                   to indicate it should be processed as an artifact.
                """
                )
            ]
        )
        self.rulesets.append(artifact_rules)

    def wrap_artifact(
        self, artifact_type: str, content: Any, metadata: Optional[dict] = None
    ) -> str:
        """Creates a formatted artifact string with proper metadata and structure."""
        if not isinstance(content, str):
            content = str(content)

        artifact_data = {
            "type": artifact_type.lower().strip(),
            "metadata": metadata or {},
            "content": content,
        }

        return f"[ARTIFACT_START] {json.dumps(artifact_data, ensure_ascii=False)} [ARTIFACT_END]"

    def detect_content_type(self, content: str) -> Dict[str, Any]:
        """Analyzes content to determine its type and appropriate metadata."""
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

        # Default to document type if no specific patterns match
        return {"type": "document", "metadata": {"format": "markdown"}}

    def process_content(self, content: str) -> str:
        """Processes content to properly format it as artifacts."""
        # Handle explicit code blocks first
        if "```" in content:
            return self.process_code_blocks(content)

        # Detect content type and wrap appropriately
        content_info = self.detect_content_type(content)
        return self.wrap_artifact(
            content_info["type"], content, content_info["metadata"]
        )

    def process_code_blocks(self, text: str) -> str:
        """Processes text containing code blocks into artifacts."""
        parts = []
        current_pos = 0

        pattern = r"```(\w+)?\n(.*?)\n```"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            # Add text before code block
            start_text = text[current_pos : match.start()].strip()
            if start_text:
                parts.append(start_text)

            language = match.group(1) or "text"
            code_content = match.group(2).strip()

            # Create code artifact
            artifact = self.wrap_artifact("code", code_content, {"language": language})
            parts.append(artifact)
            current_pos = match.end()

        # Add remaining text
        remaining = text[current_pos:].strip()
        if remaining:
            parts.append(remaining)

        return "\n".join(filter(None, parts))

    def try_run(self, *args) -> Agent:
        """Executes the agent's response generation with artifact support."""
        result = super().try_run(*args)

        if result.output_task and result.output_task.output:
            output = result.output_task.output.to_text()

            # Check if the LLM indicated this should be an artifact
            if output.startswith("[NEEDS_ARTIFACT]"):
                # Remove the indicator and process the content
                content = output.replace("[NEEDS_ARTIFACT]", "", 1).strip()
                processed_output = self.process_content(content)
                result.output_task.output = TextArtifact(processed_output)

            # Otherwise leave the response as is

        return result
