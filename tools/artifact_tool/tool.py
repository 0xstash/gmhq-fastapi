from __future__ import annotations

from typing import TYPE_CHECKING, Union, Optional, Literal as LiteralType
from attrs import define, field
from schema import Schema, Literal, Or, Optional as SchemaOptional
from textwrap import dedent
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import base64
import logging
from pathlib import Path

from griptape.artifacts import (
    BaseArtifact,
    TextArtifact,
    ErrorArtifact,
    ImageArtifact,
    AudioArtifact,
)
from griptape.tools import BaseTool
from griptape.utils.decorators import activity

if TYPE_CHECKING:
    from griptape.drivers import BasePromptDriver

logger = logging.getLogger(__name__)


class ArtifactError(Exception):
    """Base exception for artifact-related errors"""

    pass


@define
class ArtifactGenerationTool(BaseTool):
    """Tool for generating various types of artifacts using Griptape"""

    # Required fields
    prompt_driver: BasePromptDriver = field(kw_only=True, default=None)

    # Optional fields with defaults
    output_dir: Optional[Path] = field(default=None, kw_only=True)
    max_content_size: int = field(default=10 * 1024 * 1024, kw_only=True)  # 10MB

    # Artifact type configurations
    ARTIFACT_TYPES: dict[str, str] = {
        "code": "application/vnd.ant.code",
        "markdown": "text/markdown",
        "html": "text/html",
        "svg": "image/svg+xml",
        "mermaid": "application/vnd.ant.mermaid",
        "react": "application/vnd.ant.react",
        "image": "image/*",
        "audio": "audio/*",
    }

    # MIME type mappings for binary content
    MIME_TYPES: dict[str, list[str]] = {
        "image": [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/svg+xml",
            "image/webp",
        ],
        "audio": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/webm", "audio/aac"],
    }

    def validate_mime_type(self, artifact_type: str, mime_type: str) -> bool:
        """Validate that the MIME type is allowed for the artifact type"""
        if artifact_type not in ["image", "audio"]:
            return True
        return mime_type in self.MIME_TYPES[artifact_type]

    def _validate_binary_data(self, data: str) -> bool:
        """Validate base64 encoded binary data"""
        try:
            # Check if the string is base64 encoded
            decoded = base64.b64decode(data)
            # Check size
            if len(decoded) > self.max_content_size:
                raise ArtifactError(
                    f"Binary data exceeds maximum size of {self.max_content_size} bytes"
                )
            return True
        except Exception as e:
            raise ArtifactError(f"Invalid base64 encoded data: {str(e)}")

    @activity(
        config={
            "description": dedent(
                """
                Generate artifacts with support for text, code, images, and audio.
                Artifacts are wrapped with [ARTIFACT_START] and [ARTIFACT_END] markers.
                Binary content (images/audio) must be base64 encoded.
            """
            ),
            "schema": Schema(
                {
                    Literal(
                        "prompt", description="Content generation prompt or description"
                    ): str,
                    Literal("type", description="Type of artifact to generate"): Or(
                        *ARTIFACT_TYPES.keys()
                    ),
                    Literal(
                        "identifier", description="Unique identifier for the artifact"
                    ): str,
                    Literal("title", description="Title of the artifact"): str,
                    SchemaOptional(
                        Literal(
                            "language",
                            description="Programming language for code artifacts",
                        )
                    ): str,
                    SchemaOptional(
                        Literal(
                            "binary_data",
                            description="Base64 encoded binary data for image/audio artifacts",
                        )
                    ): str,
                    SchemaOptional(
                        Literal(
                            "mime_type",
                            description="Specific MIME type for image/audio content",
                        )
                    ): str,
                }
            ),
        }
    )
    def generate_artifact(
        self, params: dict
    ) -> Union[TextArtifact, ImageArtifact, AudioArtifact, ErrorArtifact]:
        """Generate an artifact based on the provided parameters"""
        try:
            values = params["values"]
            artifact_type = values["type"]

            # Validate identifier format
            identifier = values["identifier"]
            if not identifier.replace("-", "").isalnum():
                raise ArtifactError(
                    "Identifier must contain only alphanumeric characters and hyphens"
                )

            # Handle binary artifacts
            if artifact_type in ["image", "audio"]:
                if "binary_data" not in values or "mime_type" not in values:
                    raise ArtifactError(
                        "binary_data and mime_type are required for image/audio artifacts"
                    )

                if not self.validate_mime_type(artifact_type, values["mime_type"]):
                    raise ArtifactError(f"Unsupported MIME type for {artifact_type}")

                return self._generate_binary_artifact(values)

            # Handle text-based artifacts
            if artifact_type == "code" and "language" not in values:
                raise ArtifactError("language is required for code artifacts")

            return self._generate_text_artifact(values)

        except ArtifactError as e:
            logger.error(f"Artifact generation error: {str(e)}")
            return ErrorArtifact(str(e))
        except Exception as e:
            logger.exception("Unexpected error during artifact generation")
            return ErrorArtifact(f"Unexpected error: {str(e)}")

    def _generate_binary_artifact(
        self, values: dict
    ) -> Union[ImageArtifact, AudioArtifact, ErrorArtifact]:
        """Handle generation of image and audio artifacts"""
        try:
            # Validate and decode binary data
            self._validate_binary_data(values["binary_data"])
            binary_data = base64.b64decode(values["binary_data"])
            mime_type = values["mime_type"]

            # Create artifact based on type
            ArtifactClass = (
                ImageArtifact if values["type"] == "image" else AudioArtifact
            )
            artifact = ArtifactClass(binary_data, mime_type=mime_type)

            # Create marked output
            marked_output = (
                f"Generated {values['type']} artifact.\n\n"
                "[ARTIFACT_START]\n"
                f"<antArtifact identifier='{values['identifier']}' "
                f"type='{mime_type}' title='{values['title']}'>\n"
                f"[Binary {values['type']} content of type {mime_type}]\n"
                "\n"
                "[ARTIFACT_END]\n\n"
                f"The {values['type']} has been generated successfully."
            )

            artifact.description = marked_output
            return artifact

        except Exception as e:
            return ErrorArtifact(f"Binary artifact generation failed: {str(e)}")

    def _generate_text_artifact(self, values: dict) -> TextArtifact:
        """Handle generation of text-based artifacts"""
        try:
            # Create XML structure
            root = ET.Element("antArtifact")
            root.set("identifier", values["identifier"])
            root.set("type", self.ARTIFACT_TYPES[values["type"]])
            root.set("title", values["title"])

            if values["type"] == "code":
                root.set("language", values["language"])

            # Generate content
            content = f"\n{values['prompt']}\n"
            root.text = escape(content)

            # Convert to string with markers
            artifact_xml = ET.tostring(root, encoding="unicode", method="xml")
            marked_output = (
                "I'll generate that for you.\n\n"
                "[ARTIFACT_START]\n"
                f"{artifact_xml}\n"
                "[ARTIFACT_END]\n\n"
                "Let me know if you need any modifications."
            )

            return TextArtifact(marked_output)

        except Exception as e:
            return ErrorArtifact(f"Text artifact generation failed: {str(e)}")
