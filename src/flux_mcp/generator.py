"""FLUX image generator with auto-unload functionality."""

import gc
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import torch
from diffusers import FluxPipeline
from PIL import Image

from .config import config

logger = logging.getLogger(__name__)


class FluxGenerator:
    """FLUX.1-dev image generator with lazy loading and auto-unload."""

    def __init__(self, auto_unload: bool = True):
        """Initialize the generator (model is not loaded yet).

        Args:
            auto_unload: Enable automatic model unloading after timeout (default: True)
                        Set to False for CLI usage where process terminates anyway.
        """
        self.pipeline: FluxPipeline | None = None
        self._lock = threading.Lock()
        self._unload_timer: threading.Timer | None = None
        self._last_access: datetime | None = None
        self.auto_unload = auto_unload
        logger.info(f"FluxGenerator initialized (auto_unload={auto_unload})")

    def _load_model(self) -> None:
        """Load the FLUX model into memory."""
        if self.pipeline is not None:
            logger.debug("Model already loaded")
            return

        logger.info(f"Loading FLUX model: {config.model_id}")
        start_time = time.time()

        # Load the pipeline with bfloat16 for VRAM efficiency
        self.pipeline = FluxPipeline.from_pretrained(
            config.model_id,
            torch_dtype=torch.bfloat16,
            cache_dir=config.model_cache,
        )

        # Enable sequential CPU offloading to reduce VRAM usage
        # This aggressively moves model components to CPU/RAM when not actively in use
        # Reduces VRAM from ~28GB to ~12GB for FLUX.1-dev
        logger.info("Enabling sequential CPU offloading for VRAM optimization")
        self.pipeline.enable_sequential_cpu_offload()

        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f}s")

        # Update last access time
        self._last_access = datetime.now()

    def _schedule_unload(self) -> None:
        """Schedule automatic model unload after timeout."""
        # Skip if auto-unload is disabled (e.g., CLI mode)
        if not self.auto_unload:
            logger.debug("Auto-unload disabled (CLI mode)")
            return

        # Cancel existing timer if any
        if self._unload_timer is not None:
            self._unload_timer.cancel()

        # Don't schedule if timeout is 0 (disabled)
        if config.unload_timeout <= 0:
            logger.debug("Auto-unload disabled (timeout = 0)")
            return

        logger.debug(f"Scheduling auto-unload in {config.unload_timeout}s")
        self._unload_timer = threading.Timer(
            config.unload_timeout,
            self._auto_unload
        )
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _auto_unload(self) -> None:
        """Auto-unload callback (runs in timer thread)."""
        logger.info("Auto-unload triggered")
        self.unload_model()

    def unload_model(self) -> None:
        """Unload the model and free GPU memory."""
        with self._lock:
            # Cancel pending timer
            if self._unload_timer is not None:
                self._unload_timer.cancel()
                self._unload_timer = None

            if self.pipeline is None:
                logger.debug("Model already unloaded")
                return

            logger.info("Unloading FLUX model")

            # Delete pipeline
            del self.pipeline
            self.pipeline = None
            self._last_access = None

            # Free GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            # Python garbage collection
            gc.collect()

            logger.info("Model unloaded and GPU cache cleared")

    def generate(
        self,
        prompt: str,
        steps: int = 28,
        guidance_scale: float = 3.5,
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
    ) -> tuple[Path, int, dict, Image.Image]:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            steps: Number of inference steps (default: 28)
            guidance_scale: Guidance scale for generation (default: 3.5)
            width: Image width in pixels (default: 1024)
            height: Image height in pixels (default: 1024)
            seed: Random seed for reproducibility (default: random)

        Returns:
            Tuple of (output_path, seed_used, generation_settings, pil_image)
        """
        with self._lock:
            # Load model if needed
            if self.pipeline is None:
                self._load_model()

            # Update last access time
            self._last_access = datetime.now()

            # Generate random seed if not provided
            if seed is None:
                seed = torch.randint(0, 2**32 - 1, (1,)).item()

            logger.info(f"Generating image with seed={seed}, steps={steps}")

            # Set up generator for reproducibility
            generator = torch.Generator(device="cuda").manual_seed(seed)

            # Generate image
            start_time = time.time()
            result = self.pipeline(
                prompt=prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                generator=generator,
            )
            gen_time = time.time() - start_time

            # Get the generated PIL Image
            pil_image = result.images[0]

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{seed}.png"
            output_path = config.output_dir / filename
            pil_image.save(output_path)

            logger.info(f"Image generated in {gen_time:.2f}s: {output_path}")

            # Schedule auto-unload
            self._schedule_unload()

            # Return generation info
            settings = {
                "prompt": prompt,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "width": width,
                "height": height,
                "generation_time": f"{gen_time:.2f}s",
            }

            return output_path, seed, settings, pil_image

    def get_status(self) -> dict:
        """Get current generator status.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            is_loaded = self.pipeline is not None

            # Calculate time until auto-unload
            time_until_unload = None
            if is_loaded and self._last_access is not None:
                elapsed = (datetime.now() - self._last_access).total_seconds()
                remaining = max(0, config.unload_timeout - elapsed)
                time_until_unload = f"{remaining:.1f}s"

            # Get VRAM usage if possible
            vram_usage = None
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / (1024**3)  # GB
                reserved = torch.cuda.memory_reserved() / (1024**3)  # GB
                vram_usage = {
                    "allocated_gb": f"{allocated:.2f}",
                    "reserved_gb": f"{reserved:.2f}",
                }

            return {
                "model_loaded": is_loaded,
                "time_until_unload": time_until_unload,
                "timeout_seconds": config.unload_timeout,
                "vram_usage": vram_usage,
                "last_access": self._last_access.isoformat() if self._last_access else None,
            }
