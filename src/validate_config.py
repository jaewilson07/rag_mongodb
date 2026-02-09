"""Entry point for validate_config. Re-exports from mdrag.config.validate_config."""

from mdrag.config.validate_config import validate_config

__all__ = ["validate_config"]

if __name__ == "__main__":
    import sys

    sys.exit(0 if validate_config() else 1)
