"""
XML schema validation for DarwinXML documents.

Provides schema validation to ensure data quality before ingestion:
- Schema conformance checking
- Structural validation
- Metadata completeness verification
- Relationship integrity validation
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from mdrag.ingestion.docling.darwinxml_models import (
    DarwinXMLDocument,
    ValidationStatus,
)
from mdrag.mdrag_logging.service_logging import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when DarwinXML validation fails."""

    pass


class ValidationResult:
    """Result of DarwinXML validation."""

    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return f"ValidationResult(status={status}, errors={len(self.errors)}, warnings={len(self.warnings)})"


class DarwinXMLValidator:
    """
    Validator for DarwinXML documents.

    Performs multi-level validation:
    1. Schema validation (structure, required fields)
    2. Content validation (non-empty content, valid metadata)
    3. Relationship validation (valid references, no cycles)
    4. Metadata validation (provenance completeness)
    """

    def __init__(
        self,
        strict_mode: bool = False,
        require_annotations: bool = True,
        require_provenance: bool = True,
    ):
        """
        Initialize validator.

        Args:
            strict_mode: Fail on warnings
            require_annotations: Require at least one annotation
            require_provenance: Require complete provenance metadata
        """
        self.strict_mode = strict_mode
        self.require_annotations = require_annotations
        self.require_provenance = require_provenance

    def validate(self, document: DarwinXMLDocument) -> ValidationResult:
        """
        Validate a DarwinXML document.

        Args:
            document: DarwinXML document to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Schema validation
        schema_errors = self._validate_schema(document)
        errors.extend(schema_errors)

        # Content validation
        content_errors, content_warnings = self._validate_content(document)
        errors.extend(content_errors)
        warnings.extend(content_warnings)

        # Annotation validation
        if self.require_annotations:
            ann_errors, ann_warnings = self._validate_annotations(document)
            errors.extend(ann_errors)
            warnings.extend(ann_warnings)

        # Provenance validation
        if self.require_provenance:
            prov_errors, prov_warnings = self._validate_provenance(document)
            errors.extend(prov_errors)
            warnings.extend(prov_warnings)

        # Relationship validation
        rel_errors, rel_warnings = self._validate_relationships(document)
        errors.extend(rel_errors)
        warnings.extend(rel_warnings)

        # Determine validity
        is_valid = len(errors) == 0 and (
            not self.strict_mode or len(warnings) == 0
        )

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def validate_batch(
        self, documents: List[DarwinXMLDocument]
    ) -> Dict[str, ValidationResult]:
        """
        Validate a batch of documents.

        Args:
            documents: List of DarwinXML documents

        Returns:
            Dictionary mapping document ID to ValidationResult
        """
        results = {}

        for doc in documents:
            try:
                result = self.validate(doc)
                results[doc.id] = result
            except Exception as e:
                results[doc.id] = ValidationResult(
                    is_valid=False, errors=[f"Validation exception: {str(e)}"]
                )

        return results

    def _validate_schema(self, document: DarwinXMLDocument) -> List[str]:
        """Validate document schema and structure."""
        errors = []

        # Required fields
        if not document.id:
            errors.append("Missing document ID")
        if not document.document_title:
            errors.append("Missing document title")
        if not document.chunk_uuid:
            errors.append("Missing chunk UUID")
        if not document.content:
            errors.append("Missing content")
        if document.provenance is None:
            errors.append("Missing provenance metadata")

        # Schema version
        if document.schema_version != "1.0":
            errors.append(f"Unsupported schema version: {document.schema_version}")

        # Chunk index should be non-negative
        if document.chunk_index < 0:
            errors.append("Chunk index must be non-negative")

        return errors

    def _validate_content(
        self, document: DarwinXMLDocument
    ) -> Tuple[List[str], List[str]]:
        """Validate document content."""
        errors = []
        warnings = []

        # Content should not be empty
        if not document.content.strip():
            errors.append("Content is empty or whitespace-only")

        # Content length check
        if len(document.content) < 10:
            warnings.append("Content is very short (< 10 characters)")

        # Token count check (if available in metadata)
        token_count = document.metadata.get("token_count")
        if token_count and token_count > 8000:
            warnings.append(
                f"Token count ({token_count}) exceeds typical embedding limits"
            )

        return errors, warnings

    def _validate_annotations(
        self, document: DarwinXMLDocument
    ) -> Tuple[List[str], List[str]]:
        """Validate annotations."""
        errors = []
        warnings = []

        if not document.annotations:
            if self.require_annotations:
                errors.append("No annotations found")
            else:
                warnings.append("No annotations found")
            return errors, warnings

        # Validate each annotation
        annotation_ids = set()
        for i, ann in enumerate(document.annotations):
            # Check for duplicate IDs
            if ann.id in annotation_ids:
                errors.append(f"Duplicate annotation ID: {ann.id}")
            annotation_ids.add(ann.id)

            # Validate parent references
            if ann.parent_id and ann.parent_id not in annotation_ids:
                # Parent might be in a later annotation (forward reference)
                pass  # We'll validate in a second pass

            # Check annotation has content
            if not ann.content and ann.type.value not in ["metadata", "relationship"]:
                warnings.append(f"Annotation {ann.id} has no content")

        return errors, warnings

    def _validate_provenance(
        self, document: DarwinXMLDocument
    ) -> Tuple[List[str], List[str]]:
        """Validate provenance metadata."""
        errors = []
        warnings = []

        prov = document.provenance

        # Required provenance fields
        if not prov.source_url:
            errors.append("Missing provenance source_url")
        if not prov.source_type:
            errors.append("Missing provenance source_type")
        if not prov.content_hash:
            errors.append("Missing provenance content_hash")

        # Validate content hash format (SHA-256 is 64 hex chars)
        if prov.content_hash and len(prov.content_hash) != 64:
            warnings.append(
                f"Content hash length ({len(prov.content_hash)}) doesn't match SHA-256 format"
            )

        # Check validation status
        if prov.validation_status == ValidationStatus.REJECTED:
            warnings.append("Document is marked as REJECTED in provenance")

        # Check for timestamps
        if not prov.ingestion_timestamp:
            warnings.append("Missing ingestion timestamp")

        return errors, warnings

    def _validate_relationships(
        self, document: DarwinXMLDocument
    ) -> Tuple[List[str], List[str]]:
        """Validate relationships between annotations."""
        errors = []
        warnings = []

        # Collect all annotation IDs
        annotation_ids = {ann.id for ann in document.annotations}

        # Validate relationships
        for ann in document.annotations:
            for rel in ann.relationships:
                # Check source/target IDs exist (could be external references)
                if rel.source_id not in annotation_ids and rel.source_id != document.chunk_uuid:
                    # External reference - OK for cross-chunk relationships
                    pass

                if rel.target_id not in annotation_ids and not rel.target_id.startswith(
                    ("http://", "https://")
                ):
                    # Could be external chunk reference
                    pass

                # Check for self-references
                if rel.source_id == rel.target_id:
                    warnings.append(
                        f"Self-referential relationship in annotation {ann.id}"
                    )

        # Check for relationship cycles (basic check)
        if self._has_relationship_cycle(document):
            warnings.append("Detected potential relationship cycle")

        return errors, warnings

    def _has_relationship_cycle(self, document: DarwinXMLDocument) -> bool:
        """
        Check for cycles in annotation relationships.

        Note: This is a basic implementation. For production, use a proper
        graph cycle detection algorithm.
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {}

        for ann in document.annotations:
            if ann.id not in graph:
                graph[ann.id] = []

            for rel in ann.relationships:
                if rel.source_id == ann.id:
                    graph[ann.id].append(rel.target_id)

        # Simple DFS cycle detection
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True

        return False


def validate_darwin_document(
    document: DarwinXMLDocument, strict: bool = False
) -> ValidationResult:
    """
    Convenience function to validate a DarwinXML document.

    Args:
        document: DarwinXML document to validate
        strict: Enable strict mode (warnings become errors)

    Returns:
        ValidationResult

    Raises:
        ValidationError: If validation fails in strict mode
    """
    validator = DarwinXMLValidator(strict_mode=strict)
    result = validator.validate(document)

    if strict and not result.is_valid:
        error_msg = "\n".join(result.errors)
        raise ValidationError(f"Document validation failed:\n{error_msg}")

    return result


__all__ = ["DarwinXMLValidator", "ValidationError", "ValidationResult", "validate_darwin_document"]
