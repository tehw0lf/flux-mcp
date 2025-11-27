"""FLUX image generator with auto-unload functionality."""

from __future__ import annotations

import gc
import json
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import torch
from diffusers import Flux2Pipeline
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from .config import config

logger = logging.getLogger(__name__)


class FluxGenerator:
    """FLUX image generator with lazy loading and auto-unload."""

    def __init__(self, auto_unload: bool = True, model_id: str | None = None):
        """Initialize the generator (model is not loaded yet).

        Args:
            auto_unload: Enable automatic model unloading after timeout (default: True)
                        Set to False for CLI usage where process terminates anyway.
            model_id: Model ID to use (default: from config, usually FLUX.2-dev)
                     Supported: "black-forest-labs/FLUX.1-dev" (fast), "black-forest-labs/FLUX.2-dev" (quality)
        """
        self.pipeline: Flux2Pipeline | None = None
        self._lock = threading.Lock()
        self._unload_timer: threading.Timer | None = None
        self._last_access: datetime | None = None
        self.auto_unload = auto_unload
        self.model_id = model_id or config.model_id
        self._current_model_id: str | None = None  # Track which model is actually loaded
        logger.info(f"FluxGenerator initialized (model={self.model_id}, auto_unload={auto_unload})")

    def _load_model(self, model_id: str | None = None) -> None:
        """Load the FLUX model into memory.

        Args:
            model_id: Optional model ID to load. If different from current, will unload first.
        """
        # Determine which model to load
        target_model = model_id or self.model_id

        # If a different model is loaded, unload it first
        if self.pipeline is not None and self._current_model_id != target_model:
            logger.info(f"Switching from {self._current_model_id} to {target_model}")
            self.unload_model()
        elif self.pipeline is not None:
            logger.debug(f"Model {target_model} already loaded")
            return

        logger.info(f"Loading FLUX model: {target_model}")
        start_time = time.time()

        # Enable TF32 for faster matmul on Ampere+ GPUs
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            logger.info("Enabled TF32 for faster matrix operations")

        # Load the pipeline with bfloat16 for VRAM efficiency
        logger.info(f"Loading {target_model} with bfloat16 precision")
        self.pipeline = Flux2Pipeline.from_pretrained(
            target_model,
            torch_dtype=torch.bfloat16,
            cache_dir=config.model_cache,
        )
        self._current_model_id = target_model

        # Apply memory optimization based on available VRAM
        if torch.cuda.is_available():
            total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"Detected {total_vram_gb:.1f}GB VRAM")

            # VRAM requirements for FLUX.2-dev with bfloat16:
            # - Full GPU: ~28GB (fastest)
            # - Model CPU offload: ~20GB (balanced)
            # - Sequential CPU offload: ~12GB (slower but fits in 16GB)

            if total_vram_gb >= 24:
                logger.info("Using full GPU mode (24GB+ VRAM) - fastest")
                self.pipeline.to("cuda")
            elif total_vram_gb >= 20:
                logger.info(f"Using model CPU offload ({total_vram_gb:.1f}GB VRAM) - balanced")
                self.pipeline.enable_model_cpu_offload()
            else:
                logger.info(
                    f"Using sequential CPU offload ({total_vram_gb:.1f}GB VRAM) - fits in 16GB"
                )
                self.pipeline.enable_sequential_cpu_offload()

            # Enable memory-efficient attention (flash attention if available, otherwise SDPA)
            try:
                self.pipeline.enable_xformers_memory_efficient_attention()
                logger.info("Enabled xFormers memory-efficient attention")
            except Exception:
                # xFormers not available, try PyTorch's SDPA
                try:
                    # PyTorch 2.0+ has built-in scaled dot product attention
                    if hasattr(torch.nn.functional, "scaled_dot_product_attention"):
                        logger.info("Using PyTorch SDPA (scaled dot product attention)")
                    else:
                        logger.info("No accelerated attention available")
                except Exception:
                    logger.info("Using default attention mechanism")
        else:
            logger.warning("CUDA not available - loading to CPU (very slow)")

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
        self._unload_timer = threading.Timer(config.unload_timeout, self._auto_unload)
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
            self._current_model_id = None
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
        steps: int | None = None,
        guidance_scale: float | None = None,
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
        model: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[Path, int, dict, Image.Image]:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            steps: Number of inference steps (default: from config, usually 50)
            guidance_scale: Guidance scale for generation (default: from config, usually 7.5)
            width: Image width in pixels (default: 1024)
            height: Image height in pixels (default: 1024)
            seed: Random seed for reproducibility (default: random)
            model: Model to use - "flux1-dev" (fast preview) or "flux2-dev" (quality, default)
            progress_callback: Optional callback function(step, total_steps) for progress updates

        Returns:
            Tuple of (output_path, seed_used, generation_settings, pil_image)
        """
        with self._lock:
            # Resolve model preset to full model ID
            model_id = None
            if model:
                model_id = config.models.get(model, model)  # Allow preset or full ID

            # Load model if needed (or switch models)
            self._load_model(model_id)

            # Update last access time
            self._last_access = datetime.now()

            # Use model-specific smart defaults if not specified
            current_model_defaults = config.model_defaults.get(self._current_model_id, {})
            if steps is None:
                steps = current_model_defaults.get("steps", config.default_steps)
            if guidance_scale is None:
                guidance_scale = current_model_defaults.get("guidance", config.default_guidance)

            # Generate random seed if not provided
            if seed is None:
                seed = torch.randint(0, 2**32 - 1, (1,)).item()

            logger.info(
                f"Generating image with seed={seed}, steps={steps}, guidance={guidance_scale}"
            )

            # Set up generator for reproducibility
            generator = torch.Generator(device="cuda").manual_seed(seed)

            # Create callback wrapper for diffusers pipeline
            def step_callback(pipe, step_index, timestep, callback_kwargs):
                if progress_callback:
                    # Call user's progress callback with current step and total
                    progress_callback(step_index + 1, steps)
                return callback_kwargs

            # Generate image
            start_time = time.time()
            result = self.pipeline(
                prompt=prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                generator=generator,
                callback_on_step_end=step_callback if progress_callback else None,
            )
            gen_time = time.time() - start_time

            # Get the generated PIL Image
            pil_image = result.images[0]

            # Prepare metadata
            timestamp_iso = datetime.now().isoformat()
            metadata_dict = {
                "prompt": prompt,
                "seed": seed,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "width": width,
                "height": height,
                "model": self._current_model_id,
                "generation_time_seconds": round(gen_time, 2),
                "timestamp": timestamp_iso,
            }

            # Create PNG metadata
            png_info = PngInfo()
            png_info.add_text("parameters", json.dumps(metadata_dict, indent=2))
            # Add individual fields for compatibility with various tools
            png_info.add_text("prompt", prompt)
            png_info.add_text("seed", str(seed))
            png_info.add_text("steps", str(steps))
            png_info.add_text("guidance_scale", str(guidance_scale))
            png_info.add_text("model", self._current_model_id)
            png_info.add_text("timestamp", timestamp_iso)

            # Save image with embedded metadata
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{seed}.png"
            output_path = config.output_dir / filename
            pil_image.save(output_path, pnginfo=png_info)

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
                "current_model": self._current_model_id,
                "time_until_unload": time_until_unload,
                "timeout_seconds": config.unload_timeout,
                "vram_usage": vram_usage,
                "last_access": self._last_access.isoformat() if self._last_access else None,
            }
