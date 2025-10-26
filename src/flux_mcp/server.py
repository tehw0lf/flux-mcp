"""MCP Server for FLUX image generation."""

import base64
import io
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ImageContent, TextContent, Tool
from PIL import Image

from .config import config
from .generator import FluxGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize server and generator
app = Server("flux-mcp")
generator = FluxGenerator()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="generate_image",
            description=(
                "Generate an image using FLUX.1-dev model. "
                "Creates high-quality images from text prompts. "
                "Images are saved to the configured output directory."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the image to generate",
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of inference steps (default: 28, recommended: 20-50)",
                        "default": 28,
                    },
                    "guidance_scale": {
                        "type": "number",
                        "description": "Guidance scale for generation (default: 3.5, recommended: 1.0-10.0)",
                        "default": 3.5,
                    },
                    "width": {
                        "type": "integer",
                        "description": "Image width in pixels (default: 1024)",
                        "default": 1024,
                    },
                    "height": {
                        "type": "integer",
                        "description": "Image height in pixels (default: 1024)",
                        "default": 1024,
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility (optional, random if not provided)",
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="unload_model",
            description=(
                "Immediately unload the FLUX model from GPU memory. "
                "Use this to free up VRAM when you're done generating images. "
                "The model will be automatically reloaded on the next generation request."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_status",
            description=(
                "Get current status of the FLUX generator. "
                "Shows whether the model is loaded, time until auto-unload, "
                "and current VRAM usage."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="set_timeout",
            description=(
                "Set the auto-unload timeout for the FLUX model. "
                "The model will automatically unload after this many seconds of inactivity. "
                "Set to 0 to disable auto-unload."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Timeout in seconds (0 to disable auto-unload)",
                    },
                },
                "required": ["timeout_seconds"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent]:
    """Handle tool calls."""
    try:
        if name == "generate_image":
            # Extract parameters
            prompt = arguments["prompt"]
            steps = arguments.get("steps", 28)
            guidance_scale = arguments.get("guidance_scale", 3.5)
            width = arguments.get("width", 1024)
            height = arguments.get("height", 1024)
            seed = arguments.get("seed")

            # Validate parameters
            if not prompt.strip():
                return [TextContent(
                    type="text",
                    text="Error: Prompt cannot be empty"
                )]

            if steps < 1 or steps > 100:
                return [TextContent(
                    type="text",
                    text="Error: Steps must be between 1 and 100"
                )]

            if width < 256 or width > 2048 or height < 256 or height > 2048:
                return [TextContent(
                    type="text",
                    text="Error: Width and height must be between 256 and 2048"
                )]

            # Generate image
            logger.info(f"Generating image: {prompt[:50]}...")
            output_path, used_seed, settings, pil_image = generator.generate(
                prompt=prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                seed=seed,
            )

            # Create thumbnail (512x512) for instant preview
            thumbnail_size = (512, 512)
            thumbnail = pil_image.copy()
            thumbnail.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Save thumbnail to disk
            thumb_filename = output_path.stem + "_thumb" + output_path.suffix
            thumb_path = output_path.parent / thumb_filename
            thumbnail.save(thumb_path)

            # Encode thumbnail as base64 for instant preview
            buffer = io.BytesIO()
            thumbnail.save(buffer, format="PNG")
            thumbnail_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Format response
            response = f"""Image generated successfully!

📁 Full-size image: {output_path}
🖼️  Thumbnail: {thumb_path}
🎲 Seed: {used_seed}
⚙️ Settings:
  - Steps: {settings['steps']}
  - Guidance Scale: {settings['guidance_scale']}
  - Resolution: {settings['width']}x{settings['height']}
  - Generation Time: {settings['generation_time']}

💡 Use the same seed to reproduce this image.
📌 A {thumbnail_size[0]}x{thumbnail_size[1]} thumbnail is shown below for instant preview.
"""
            return [
                TextContent(type="text", text=response),
                ImageContent(
                    type="image",
                    data=thumbnail_data,
                    mimeType="image/png"
                )
            ]

        elif name == "unload_model":
            generator.unload_model()
            return [TextContent(
                type="text",
                text="✅ FLUX model unloaded successfully. GPU memory freed."
            )]

        elif name == "get_status":
            status = generator.get_status()

            # Format status message
            if status["model_loaded"]:
                status_msg = f"""🟢 FLUX Model Status: LOADED

⏱️  Time until auto-unload: {status['time_until_unload']}
⚙️  Auto-unload timeout: {status['timeout_seconds']}s
📅 Last access: {status['last_access']}
"""
                if status["vram_usage"]:
                    vram = status["vram_usage"]
                    status_msg += f"""
🎮 VRAM Usage:
  - Allocated: {vram['allocated_gb']} GB
  - Reserved: {vram['reserved_gb']} GB
"""
            else:
                status_msg = f"""🔴 FLUX Model Status: NOT LOADED

⚙️  Auto-unload timeout: {status['timeout_seconds']}s
💡 Model will load automatically on next generation request.
"""
                if status["vram_usage"]:
                    vram = status["vram_usage"]
                    status_msg += f"""
🎮 VRAM Usage:
  - Allocated: {vram['allocated_gb']} GB
  - Reserved: {vram['reserved_gb']} GB
"""

            return [TextContent(type="text", text=status_msg)]

        elif name == "set_timeout":
            timeout_seconds = arguments["timeout_seconds"]

            if timeout_seconds < 0:
                return [TextContent(
                    type="text",
                    text="Error: Timeout must be non-negative (0 to disable)"
                )]

            config.update_timeout(timeout_seconds)

            if timeout_seconds == 0:
                msg = "✅ Auto-unload disabled. Model will stay loaded until manually unloaded."
            else:
                msg = f"✅ Auto-unload timeout set to {timeout_seconds} seconds."

            return [TextContent(type="text", text=msg)]

        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]

    except Exception as e:
        logger.error(f"Error in tool '{name}': {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def async_main():
    """Run the MCP server."""
    logger.info("Starting FLUX MCP Server")
    logger.info(f"Output directory: {config.output_dir}")
    logger.info(f"Auto-unload timeout: {config.unload_timeout}s")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def main():
    """Entry point for the MCP server."""
    import asyncio
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
