"""Configuration management for FLUX MCP Server."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration class for FLUX MCP Server."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Model unload timeout in seconds (default: 5 minutes)
        self.unload_timeout: int = int(os.getenv("FLUX_UNLOAD_TIMEOUT", "300"))

        # Output directory for generated images
        output_dir = os.getenv("FLUX_OUTPUT_DIR", str(Path.home() / "flux_output"))
        self.output_dir: Path = Path(output_dir)

        # HuggingFace model cache directory (optional)
        cache_dir = os.getenv("FLUX_MODEL_CACHE")
        self.model_cache: Path | None = Path(cache_dir) if cache_dir else None

        # Model configuration
        # Supported models:
        # - FLUX.1-dev: Original FLUX model, faster generation (4-8 steps), good for previews
        # - FLUX.2-dev: Latest FLUX model, higher quality (50 steps), production use
        self.model_id: str = os.getenv("FLUX_MODEL_ID", "black-forest-labs/FLUX.2-dev")

        # Model presets for easy switching
        self.models = {
            "flux1-dev": "black-forest-labs/FLUX.1-dev",
            "flux2-dev": "black-forest-labs/FLUX.2-dev",
        }

        # Default generation parameters (can be overridden via env vars)
        # These are optimized for FLUX.2-dev, FLUX.1-dev works better with lower values
        self.default_steps: int = int(os.getenv("FLUX_DEFAULT_STEPS", "50"))
        self.default_guidance: float = float(os.getenv("FLUX_DEFAULT_GUIDANCE", "7.5"))

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def update_timeout(self, timeout_seconds: int) -> None:
        """Update the unload timeout.

        Args:
            timeout_seconds: New timeout value in seconds
        """
        if timeout_seconds < 0:
            raise ValueError("Timeout must be non-negative")
        self.unload_timeout = timeout_seconds


# Global config instance
config = Config()
