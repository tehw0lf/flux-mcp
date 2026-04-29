"""Configuration management for FLUX MCP Server."""

import os
from pathlib import Path

import torch
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
        self.output_dir: Path = Path(output_dir).expanduser()

        # HuggingFace model cache directory (optional)
        cache_dir = os.getenv("FLUX_MODEL_CACHE")
        self.model_cache: Path | None = Path(cache_dir).expanduser() if cache_dir else None

        # On MPS (Apple Silicon) default to FLUX.1-dev — FLUX.2-dev exceeds typical unified memory.
        # On CUDA default to FLUX.2-dev for maximum quality.
        _mps = not torch.cuda.is_available() and torch.backends.mps.is_available()
        _default_model = "black-forest-labs/FLUX.1-dev" if _mps else "black-forest-labs/FLUX.2-dev"
        self.model_id: str = os.getenv("FLUX_MODEL_ID", _default_model)

        self.models = {
            "flux1-dev": "black-forest-labs/FLUX.1-dev",
            "flux2-dev": "black-forest-labs/FLUX.2-dev",
        }

        # Model-specific optimal quality defaults (based on testing)
        # Both are optimized for high quality output
        self.model_defaults = {
            "black-forest-labs/FLUX.1-dev": {"steps": 40, "guidance": 7.5},
            "black-forest-labs/FLUX.2-dev": {"steps": 50, "guidance": 7.5},
        }

        self.default_steps: int = int(os.getenv("FLUX_DEFAULT_STEPS", "40" if _mps else "50"))
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
