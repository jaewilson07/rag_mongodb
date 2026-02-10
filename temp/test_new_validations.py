#!/usr/bin/env python
"""
Test script to demonstrate new Phase 1 validation features.

This script shows:
1. Neo4j validation (validate_neo4j, check_neo4j)
2. vLLM validation (validate_vllm, check_vllm)
3. RQ workers validation (validate_rq_workers, check_rq_workers)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mdrag.config.settings import load_settings
from mdrag.core.validation import (
    ValidationError,
    validate_neo4j,
    validate_rq_workers,
    validate_vllm,
)

# Import sample utilities for pre-flight style checks
sys.path.insert(0, str(Path(__file__).parent.parent / "sample"))
from utils import check_neo4j, check_rq_workers, check_vllm, print_pre_flight_results


def test_core_validation():
    """Test core validation functions (raise ValidationError on failure)."""
    print("=" * 70)
    print("CORE VALIDATION TESTS (src/validation.py)")
    print("=" * 70)

    settings = load_settings()

    # Test 1: Neo4j Validation
    print("\n1. Neo4j Validation")
    print("-" * 70)
    try:
        validate_neo4j(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password,
            settings.neo4j_database,
        )
        print("✓ Neo4j validation PASSED")
    except ValidationError as e:
        print(f"❌ Neo4j validation FAILED:\n{e}")

    # Test 2: vLLM Validation (conditional - only if enabled)
    print("\n2. vLLM Validation")
    print("-" * 70)
    if settings.vllm_enabled:
        try:
            validate_vllm(
                settings.vllm_reasoning_url,
                settings.vllm_embedding_url,
            )
            print("✓ vLLM validation PASSED")
        except ValidationError as e:
            print(f"❌ vLLM validation FAILED:\n{e}")
    else:
        print("⊘ vLLM disabled (vllm_enabled=False), skipping validation")

    # Test 3: RQ Workers Validation
    print("\n3. RQ Workers Validation")
    print("-" * 70)
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    try:
        validate_rq_workers(redis_url, queue_name="default")
        print("✓ RQ workers validation PASSED")
    except ValidationError as e:
        print(f"❌ RQ workers validation FAILED:\n{e}")


def test_sample_checks():
    """Test sample pre-flight check functions (return dict with status)."""
    print("\n\n")
    print("=" * 70)
    print("SAMPLE PRE-FLIGHT CHECKS (sample/utils/__init__.py)")
    print("=" * 70)

    settings = load_settings()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")

    checks = {
        "Neo4j": check_neo4j(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password,
            settings.neo4j_database,
        ),
        "RQ Workers": check_rq_workers(redis_url),
    }

    # Add vLLM check if enabled
    if settings.vllm_enabled:
        checks["vLLM"] = check_vllm(
            settings.vllm_reasoning_url,
            settings.vllm_embedding_url,
        )

    print_pre_flight_results(checks)

    if all(check["status"] == "ok" for check in checks.values()):
        print("\n✓ All pre-flight checks PASSED - ready for production!")
    else:
        print("\n⚠ Some pre-flight checks failed - review setup instructions above")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PHASE 1 VALIDATION TESTS")
    print("Testing: Neo4j, vLLM, RQ Workers validations")
    print("=" * 70)

    try:
        # Run both test suites
        test_core_validation()
        test_sample_checks()

        print("\n" + "=" * 70)
        print("TEST SUITE COMPLETE")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
