output_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Output",
    "type": "object",
    "properties": {
        "stream_elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["text", "artifact"]},
                    "content": {"type": "string"},
                    "sequence_number": {"type": "integer"},
                    "id": {"type": ["string", "null"]},
                    "artifact_type": {"type": ["string", "null"]},
                    "language": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                },
                "required": [
                    "type",
                    "content",
                    "sequence_number",
                    "id",
                    "artifact_type",
                    "language",
                    "title",
                ],
                "additionalProperties": False,
            },
        },
        "has_artifacts": {"type": "boolean"},
    },
    "required": ["stream_elements", "has_artifacts"],
    "additionalProperties": False,
}
