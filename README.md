# FLUX MCP Server & CLI

A Model Context Protocol (MCP) server and command-line tool for generating high-quality images using FLUX.1-dev and FLUX.2-dev with automatic model unloading to save VRAM and power.

## Features

- 🎨 **Dual Model Support** - FLUX.1-dev (faster quality, 4-8min) and FLUX.2-dev (maximum quality, 30-40min)
- ⚡ **Smart VRAM Management** - Automatically selects best strategy based on available VRAM
- 🔄 **Auto-Unload** - Automatically unloads model after configurable inactivity period (MCP mode)
- 💾 **Memory Efficient** - Sequential CPU offload for 16GB GPUs, full GPU mode for 24GB+
- 🎲 **Reproducible** - Seed-based generation for consistent results
- 📊 **Status Monitoring** - Check model status and VRAM usage
- 🔧 **Runtime Configuration** - Adjust timeout and switch models without restarting
- 🖥️ **Dual Interface** - Use via MCP-compatible applications or command-line (CLI)
- 🖼️ **Preview Tool** - Retrieve generated images by ID after background generation completes

## Requirements

- Python 3.10+
- NVIDIA GPU with 12GB+ VRAM (16GB recommended, 24GB+ for maximum speed)
- CUDA toolkit installed
- PyTorch with CUDA support

## Quick Start

Get started with FLUX MCP in minutes:

```bash
# 1. Install dependencies (using UV - recommended)
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env to set FLUX_OUTPUT_DIR and other preferences

# 3. Add to your MCP client config (example for Claude Desktop)
# Add to ~/.config/Claude/claude_desktop_config.json (Linux)
# See "MCP Configuration" section below for full details

# 4. Generate your first image (CLI mode)
flux generate "a beautiful sunset over mountains"

# Or use via MCP client (e.g., Claude Desktop)
# Just ask: "Generate an image of a beautiful sunset over mountains"
```

For detailed setup and configuration, see the sections below.

## MCP Configuration

Add the server to your MCP client configuration. Below is an example for Claude Desktop:

**Claude Desktop configuration file locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "flux": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/flux-mcp",
        "run",
        "flux-mcp"
      ]
    }
  }
}
```

> **Security note**: Keep `FLUX_OUTPUT_DIR` and other settings in `.env`, not inlined into MCP client configs. The `.env` file is loaded automatically at startup.

Or if installed globally with pip:

```json
{
  "mcpServers": {
    "flux": {
      "command": "python",
      "args": [
        "-m",
        "flux_mcp.server"
      ]
    }
  }
}
```

After adding the configuration, restart your MCP client (e.g., Claude Desktop).

## Available MCP Tools

The following tools are available when using this server with any MCP-compatible client. Examples below show usage with Claude Desktop.

> **Note on FLUX.2-dev timeouts**: MCP clients enforce a timeout (typically 1-5 min) on tool calls. FLUX.2-dev takes 30-40 min on a 16GB GPU — far exceeding any MCP timeout. The server is non-blocking: generation continues in the background after the client timeout. Use `get_preview` with the returned `image_id` to retrieve the result when ready. See [Known Behavior: MCP Timeouts](#known-behavior-mcp-timeouts-during-flux2-dev-generation) for full details.

### 1. `generate_image`

Generate an image from a text prompt using FLUX.1-dev (fast) or FLUX.2-dev (quality).

**Parameters:**
- `prompt` (required): Text description of the image
- `model` (optional): "flux1-dev" (faster quality, 40 steps) or "flux2-dev" (maximum quality, 50 steps, default)
- `steps` (optional): Number of inference steps (auto: FLUX.1=40, FLUX.2=50, range: 20-100)
- `guidance_scale` (optional): Guidance scale (default: 7.5 for both models, range: 1.0-10.0)
- `width` (optional): Image width in pixels (default: 1024, range: 256-2048)
- `height` (optional): Image height in pixels (default: 1024, range: 256-2048)
- `seed` (optional): Random seed for reproducibility (random if not provided)

**Returns:** File path, seed, generation settings, inline thumbnail preview, and an `image_id` you can pass to `get_preview` later.

**Example Usage (natural language with MCP client):**
```
Generate a high quality image with flux1-dev of a futuristic cyberpunk city at sunset with neon lights
```

```
Generate maximum quality image with flux2-dev and seed 42 of a serene mountain landscape
```

### 2. `get_preview`

Retrieve a preview (thumbnail) of a generated image. Especially useful after a FLUX.2-dev background generation where the MCP client timed out.

**Parameters:**
- `image_id` (optional): Image ID returned by `generate_image` (e.g. `20250126_143052_42`). Omit to get the last generated image.

**Returns:** Inline thumbnail and full-size image path.

**Example Usage:**
```
Get the preview for image 20250126_143052_42
```

```
Show me the last generated image
```

### 3. `get_status`

Check the current status of the FLUX generator.

**Returns:**
- Model load status
- Time remaining until auto-unload
- Current VRAM usage
- Last access time

**Example Usage:**
```
Check the FLUX model status
```

### 4. `unload_model`

Immediately unload the FLUX model from GPU memory.

**Example Usage:**
```
Unload the FLUX model to free up VRAM
```

### 5. `set_timeout`

Change the auto-unload timeout at runtime.

**Parameters:**
- `timeout_seconds` (required): New timeout in seconds (0 to disable)

**Example Usage:**
```
Set FLUX auto-unload timeout to 600 seconds
```

```
Disable FLUX auto-unload
```

## CLI Usage

In addition to the MCP server mode, you can use FLUX directly from the command line for **completely offline and private** image generation.

### Quick Start

```bash
# Basic usage
flux generate "a beautiful sunset over mountains"

# With custom parameters
flux generate "portrait of a cat" --steps 35 --guidance 4.0 --seed 42

# Interactive mode for batch generation
flux generate --interactive

# Check system status
flux status

# View configuration
flux config

# Open output directory
flux open-output
```

### Generate Command

The main command for image generation:

```bash
flux generate [OPTIONS] PROMPT
```

**Options:**

- `--steps, -s INTEGER` - Number of inference steps (default: 50)
- `--guidance, -g FLOAT` - Guidance scale (default: 7.5)
- `--width, -w INTEGER` - Image width in pixels, must be multiple of 8 (default: 1024)
- `--height, -h INTEGER` - Image height in pixels, must be multiple of 8 (default: 1024)
- `--seed INTEGER` - Random seed for reproducibility
- `--output, -o PATH` - Custom output path (default: auto-generated)
- `--output-dir PATH` - Override output directory
- `--interactive, -i` - Interactive mode
- `--fast, -f` - Quick generation with FLUX.1-dev (no env var needed)
- `--verbose, -v` - Verbose output with debug info

**Examples:**

```bash
# Simple generation
flux generate "a cozy cabin in snowy mountains"

# High quality with more steps
flux generate "professional portrait" --steps 40 --guidance 7.5

# Custom resolution
flux generate "wide landscape" --width 1536 --height 1024

# Reproducible generation
flux generate "cute robot" --seed 42

# Fast generation with FLUX.1-dev
flux generate "sunset" --fast

# Save to specific location
flux generate "sunset" --output ~/Pictures/my-sunset.png

# Interactive mode (best for multiple images)
flux generate --interactive
```

### Interactive Mode

Interactive mode allows you to generate multiple images without reloading the model:

```bash
flux generate --interactive
```

**Interactive workflow:**

1. Enter your prompt
2. Configure parameters (steps, guidance, dimensions, seed)
3. Image generates and saves
4. Choose to generate another or exit
5. Model stays loaded between generations for faster subsequent images

### Other Commands

**Status Command:**

```bash
flux status
```

Shows:
- Model information
- Output directory
- CUDA availability
- GPU name and VRAM usage
- Model cache location

**Config Command:**

```bash
flux config
```

Displays current configuration from environment variables.

**Open Output:**

```bash
flux open-output
```

Opens the output directory in your file manager (Linux: xdg-open, macOS: open, Windows: explorer).

### Output Files

Generated images are saved with embedded metadata:

- **Image:** `YYYYMMDD_HHMMSS_SEED.png`
- **Thumbnail:** `YYYYMMDD_HHMMSS_SEED_thumb.png` (512x512 preview)

All generation parameters are embedded directly in the PNG metadata. You can view them with tools like `exiftool`:

```bash
exiftool image.png
```

Embedded metadata includes:
- `Prompt`: The text prompt used
- `Seed`: Random seed for reproducibility
- `Steps`: Number of inference steps
- `Guidance Scale`: Guidance scale value
- `Width` / `Height`: Image dimensions
- `Model`: FLUX model used
- `Generation Time Seconds`: How long generation took
- `Timestamp`: When the image was created

### CLI vs MCP Server

**CLI Mode:**
- ✓ Completely offline and private (no MCP client needed)
- ✓ Direct control from terminal
- ✓ Batch generation with interactive mode
- ✓ No auto-unload (process terminates after generation)
- ✓ Generates thumbnails for quick preview
- ✓ Rich terminal UI with progress bars
- ✓ No timeout restrictions for long FLUX.2-dev generations

**MCP Server Mode:**
- ✓ Integrated with MCP-compatible applications (like Claude Desktop)
- ✓ Natural language interface
- ✓ Auto-unload after timeout (saves power)
- ✓ Persistent background process
- ✓ Access from conversational AI interfaces
- ✓ Preview retrieval via `get_preview` after background generation

Both modes share the same configuration, model cache, and output directory.

## Configuration

Edit `.env` to customize (copy from `.env.example`):

```bash
# Auto-unload timeout in seconds (default: 300 = 5 minutes)
FLUX_UNLOAD_TIMEOUT=300

# Output directory for generated images
FLUX_OUTPUT_DIR=/path/to/flux_output

# Optional: Custom HuggingFace cache directory
# FLUX_MODEL_CACHE=/path/to/cache

# Model selection (choose default model)
# FLUX_MODEL_ID=black-forest-labs/FLUX.1-dev   # Faster quality (4-8 min, 40 steps default)
# FLUX_MODEL_ID=black-forest-labs/FLUX.2-dev   # Maximum quality (default, 30-40 min, 50 steps)

# Default generation parameters (model-specific smart defaults apply automatically)
# FLUX_DEFAULT_STEPS=50        # Override auto defaults: FLUX.1-dev=40, FLUX.2-dev=50
# FLUX_DEFAULT_GUIDANCE=7.5    # Both models use 7.5 for optimal quality
```

### Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `FLUX_UNLOAD_TIMEOUT` | `300` | Auto-unload timeout in seconds (0 = disabled) |
| `FLUX_OUTPUT_DIR` | `~/flux_output` | Directory for generated images |
| `FLUX_MODEL_CACHE` | *(HuggingFace default)* | Custom model cache directory |
| `FLUX_MODEL_ID` | `black-forest-labs/FLUX.2-dev` | Default model |
| `FLUX_DEFAULT_STEPS` | `50` | Override inference steps (model defaults apply if unset) |
| `FLUX_DEFAULT_GUIDANCE` | `7.5` | Guidance scale |

### Advanced Configuration

**Custom Model Cache** (share across projects or save space):

```bash
# In .env
FLUX_MODEL_CACHE=/mnt/data/huggingface/cache
```

**Disable Auto-Unload** (keep model loaded permanently):

```bash
# In .env
FLUX_UNLOAD_TIMEOUT=0
```

Or at runtime:
```
Set FLUX timeout to 0
```

**Logging** (capture server logs):

```json
{
  "mcpServers": {
    "flux": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/flux-mcp && uv run flux-mcp 2>> /tmp/flux-mcp.log"
      ]
    }
  }
}
```

## Installation

1. **Clone the repository** (or navigate to the project directory):

```bash
cd /path/to/flux-mcp
```

2. **Install with UV** (recommended):

```bash
uv sync
```

Or install with pip:

```bash
pip install -e .
```

3. **Configure environment variables**:

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## How It Works

### Smart VRAM Detection

On model load, the server:

1. **Detects total VRAM** available on your GPU
2. **Selects optimal mode** automatically:
   - **24GB+**: Full GPU mode (all components stay on GPU, fastest for both models)
   - **20-24GB**: Model CPU offload mode (balanced, components moved between CPU/GPU as needed)
   - **12-20GB**: Sequential CPU offload mode (stable, slower but fits in 16GB VRAM)
3. **Logs the decision** so you know which mode is active

**Sequential CPU Offload** moves entire model components (text encoder, transformer, VAE) to CPU when not actively being used. This is the most stable approach for limited VRAM systems and works reliably with both FLUX.1-dev and FLUX.2-dev.

For GPUs with <24GB VRAM, the server also enables:
- **Memory-efficient attention** (xFormers or PyTorch SDPA)
- **bfloat16 precision** for ~50% VRAM savings vs float32

These optimizations allow both models to run on 12-16GB VRAM. **Note**: The experimental group offload with CUDA streams has been removed due to stability issues - sequential CPU offload is the recommended stable configuration.

### Auto-Unload Mechanism

1. **Lazy Loading**: The model is NOT loaded when the server starts
2. **On-Demand Loading**: Model loads automatically on first generation request
3. **Timer Reset**: Each generation resets the auto-unload timer
4. **Automatic Cleanup**: After the configured timeout with no activity:
   - Model is removed from memory
   - GPU cache is cleared (`torch.cuda.empty_cache()`)
   - Python garbage collection runs
5. **Seamless Reload**: Model automatically reloads on next request

### Memory Management

The server uses several strategies to optimize VRAM:

- **Smart mode selection** based on detected VRAM (24GB+: full GPU, 20-24GB: model CPU offload, <20GB: sequential CPU offload)
- **bfloat16 precision** instead of float32 (saves ~50% VRAM)
- **Sequential CPU offload** for <20GB GPUs (stable, moves entire model components to CPU when idle)
- **Memory-efficient attention** (xFormers or PyTorch SDPA for reduced memory usage)
- **TF32 acceleration** on Ampere+ GPUs for faster matrix operations
- **Explicit cache clearing** when unloading
- **Threading** for non-blocking auto-unload
- **Lock-based synchronization** for thread-safe operation
- **Dynamic model switching** - can switch between FLUX.1-dev and FLUX.2-dev without restart

### Output Files

Generated images are saved as:
```
{FLUX_OUTPUT_DIR}/{timestamp}_{seed}.png
```

Example: `20250126_143052_42.png`

## Performance Tips

### Model Comparison

Both models are optimized for **high-quality** output with tested parameters:

| Model | Speed (16GB GPU) | Speed (24GB+ GPU) | Quality | Default Steps | Default Guidance |
|-------|------------------|-------------------|---------|---------------|------------------|
| **FLUX.1-dev** | 4-8 min | 1-2 min | Excellent | 40 | 7.5 |
| **FLUX.2-dev** | 30-40 min | 2-4 min | Maximum | 50 | 7.5 |

**When to use which:**
- **FLUX.1-dev**: When you need high quality faster (~4-8 min), batch generation, iterating on ideas
- **FLUX.2-dev**: When you need absolute maximum quality and time isn't critical (~30-40 min)

**VRAM Modes (automatic selection):**
- **24GB+** - Full GPU mode (fastest, both models < 5 min)
- **16-24GB** - Model CPU offload mode (balanced)
- **12-16GB** - Sequential CPU offload mode (slower, FLUX.1-dev recommended)

### Optimal Settings by GPU VRAM

**RTX 4090 / A6000 (24GB+)**
- **Resolution**: Up to 1536x1536 comfortably
- **Mode**: Full GPU (automatic)
- **FLUX.1-dev**: ~1-2 min (40 steps, quality)
- **FLUX.2-dev**: ~2-4 min (50 steps, maximum quality)
- **Guidance**: 7.5 (both models)

**RTX 4070 Ti Super / 3090 (16GB-24GB)**
- **Resolution**: Up to 1024x1024 comfortably
- **Mode**: Sequential CPU offload (automatic for 16GB)
- **FLUX.1-dev**: ~4-8 min (40 steps, quality) ← Recommended for faster workflow
- **FLUX.2-dev**: ~30-40 min (50 steps, maximum quality)
- **Guidance**: 7.5 (both models)

**RTX 3060 / 4060 Ti (12GB-16GB)**
- **Resolution**: 1024x1024 (FLUX.1) or 768x768 (FLUX.2 for safety)
- **Mode**: Sequential CPU offload (automatic)
- **FLUX.1-dev**: ~6-10 min (40 steps) ← Highly recommended
- **FLUX.2-dev**: ~40-50 min (50 steps) or reduce to 768x768
- **Tip**: Use FLUX.1-dev for better speed/quality balance on lower VRAM

**All GPUs:**
- **Guidance Scale**: 7.5 (optimal for both models)
- **Batch size**: 1 (models don't support batching)
- **Timeout**: 300s for occasional use, 600s for active sessions

### Generation Time Expectations

**Full GPU Mode (24GB+ VRAM):**
- **FLUX.1-dev** (40 steps): ~1-2 min for 1024x1024
- **FLUX.2-dev** (50 steps): ~2-4 min for 1024x1024
- **First generation**: +15-30 seconds for model loading

**Sequential CPU Offload (16GB VRAM - RTX 4070 Ti Super):**
- **FLUX.1-dev** (40 steps): ~4-8 min for 1024x1024 ← Recommended
- **FLUX.2-dev** (50 steps): ~30-40 min for 1024x1024
- **First generation**: +2-3 seconds for model loading
- **Optimization**: Use FLUX.1-dev for 5-8x faster generation with excellent quality

## Known Behavior: MCP Timeouts During FLUX.2-dev Generation

When using `generate_image` with `flux2-dev` via an MCP client (e.g. Claude Desktop, Claude Code), the client will likely report a timeout error during generation. **This is expected and normal — it is not a server error.**

### Why the timeout occurs

MCP clients enforce a client-side timeout on tool calls, typically in the range of 1-5 minutes. FLUX.2-dev generation on a 16GB GPU takes 30-40 minutes, which far exceeds any standard MCP client timeout. The server itself does not time out — only the client's wait for a response does.

The `generate_image` tool description explicitly informs the LLM about this behavior so it does not treat the timeout as a failure and does not retry unnecessarily.

### What actually happens

1. The MCP client sends the `generate_image` request to the server
2. The server starts the generation in a background thread and returns immediately (non-blocking)
3. The client-side timeout fires after 1-5 minutes — the client shows an error
4. **Generation continues running in the background** — the server process is unaffected
5. When generation completes (30-40 min later), the image is saved to the configured output directory automatically

### Retrieving the result after timeout

Use the `get_preview` tool with the `image_id` shown in the `generate_image` output (or omit `image_id` to get the last generated image):

```
Get the preview for image 20250126_143052_42
```

Or check the output directory directly:

```bash
# Watch for new files appearing
watch -n 10 ls -lht ~/flux_output | head

# Or list files sorted by modification time
ls -lht ~/flux_output | head
```

### How to verify generation is still running

```bash
# Check GPU utilization — should show ~100% during generation
watch -n 2 nvidia-smi

# Check CPU and process activity
htop
```

If `nvidia-smi` shows near-100% GPU utilization, generation is actively running.

### Recommended alternatives for long generations

- **Use FLUX.1-dev** (`flux1-dev`) — completes in 4-8 min on 16GB GPUs, well within MCP timeout limits, and produces excellent quality
- **Use CLI mode** — no timeout restrictions at all:
  ```bash
  flux generate "your prompt" --model flux2-dev
  ```
  The CLI runs the generation synchronously and shows a progress bar.

---

## Troubleshooting

### CUDA Out of Memory

**Problem**: Error during generation: "CUDA out of memory"

**Note**: The server automatically detects available VRAM and selects the best mode:
- **24GB+**: Full GPU (fastest)
- **16GB**: Model CPU offload (balanced)
- **12GB+**: Model CPU offload with reduced resolution

**If you still get OOM errors:**

1. **Close other GPU applications**:
   ```bash
   # Check what's using VRAM
   nvidia-smi
   ```

2. **Reduce image dimensions**:
   ```bash
   flux generate "prompt" --width 768 --height 768
   # Or even smaller for 12GB cards
   flux generate "prompt" --width 512 --height 512
   ```

3. **Reduce inference steps** (minimal memory impact):
   ```bash
   flux generate "prompt" --steps 28  # Default is 50
   ```

4. **Check logs** to see which mode was selected:
   ```bash
   # Look for "Using full GPU mode" or "Using model CPU offload"
   tail -f /tmp/flux-mcp.log
   ```

5. **Restart the process** if VRAM isn't fully freed:
   ```bash
   # CLI: Just run again (process exits after generation)
   # MCP: Restart your MCP client
   ```

### Model Download Issues

**Problem**: Model download fails or times out

**Solutions**:
1. Check internet connection
2. Set a custom cache directory with more space:
   ```bash
   FLUX_MODEL_CACHE=/path/to/large/disk/cache
   ```
3. Download manually with HuggingFace CLI:
   ```bash
   huggingface-cli download black-forest-labs/FLUX.2-dev
   ```

### Server Not Responding

**Problem**: MCP client doesn't see the tools

**Solutions**:
1. Check your MCP client's logs for errors
2. Verify the configuration path is absolute
3. Ensure UV is in PATH or use full path to UV binary
4. Restart your MCP client after config changes
5. Test the server manually:
   ```bash
   cd /path/to/flux-mcp
   uv run flux-mcp
   ```

### Slow Generation

**Problem**: Image generation takes too long

**Solutions**:
1. Reduce `steps` parameter (try 20-25 instead of 28)
2. Ensure GPU is being used (check with `nvidia-smi`)
3. Close background applications to free GPU resources
4. Check that CUDA is properly installed

### MCP Timeout False Positives

**Problem**: MCP client shows error during long FLUX.2-dev generations, but image still generates successfully

**Solution**: Use `get_preview` after the expected generation time to retrieve the result. See [Known Behavior: MCP Timeouts](#known-behavior-mcp-timeouts-during-flux2-dev-generation) for full details.

### Permission Errors

**Problem**: Cannot write to output directory

**Solutions**:
1. Check directory permissions
2. Set a different output directory in `.env`:
   ```bash
   FLUX_OUTPUT_DIR=/home/$USER/flux_output
   ```
3. Create the directory manually:
   ```bash
   mkdir -p ~/flux_output
   chmod 755 ~/flux_output
   ```

## Architecture

```
flux-mcp/
├── src/flux_mcp/
│   ├── __init__.py       # Package metadata
│   ├── config.py         # Environment configuration (shared)
│   ├── generator.py      # FluxGenerator class (shared)
│   ├── server.py         # MCP server (tool handlers)
│   └── cli.py            # CLI tool
├── pyproject.toml        # Project dependencies
├── .env                  # Local configuration (gitignored)
└── README.md            # This file
```

### Key Components

- **FluxGenerator**: Manages model lifecycle, threading, and GPU memory (shared between CLI and MCP)
- **Config**: Loads environment variables and provides defaults (shared)
- **MCP Server**: Exposes tools via Model Context Protocol for MCP-compatible clients
- **CLI Tool**: Direct command-line interface for offline usage

### Thread Safety

The generator uses a threading lock (`threading.Lock`) to ensure:
- Only one generation at a time
- Safe model loading/unloading
- No race conditions with auto-unload timer

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
- Check the Troubleshooting section above
- Review server logs for errors
- Open an issue on GitHub

## Changelog

### v1.2.0 (2026-03-12)

**New Features**

- ✨ Added `get_preview` MCP tool — retrieve last generated image (or by `image_id`) as inline thumbnail after background FLUX.2-dev generation completes
- ✨ `generate_image` now returns `image_id` for later reference via `get_preview`
- 📚 Restructured README for operator-first flow: MCP configuration and tools before CLI and installation details

### v1.1.0 (2025-12-07)

**Improvements & Fixes**

- ✨ Added `--fast` / `-f` flag to CLI for quick FLUX.1-dev generation without environment variables
- 🐛 Fixed pipeline class selection - FLUX.1-dev now correctly uses FluxPipeline (was causing tokenizer errors)
- 📚 Added MCP timeout warning documentation for long FLUX.2-dev generations

### v1.0.0 (2025-11-29)

**Stable Release**

- ✨ Dual model support: FLUX.1-dev (faster) and FLUX.2-dev (maximum quality)
- ✨ Model-specific quality defaults (FLUX.1=40 steps, FLUX.2=50 steps, both at 7.5 guidance)
- ✨ Smart VRAM optimization for 12-24GB GPUs with automatic mode selection
- ✨ CLI tool with interactive mode and thumbnail generation
- ✨ MCP server with auto-unload and progress reporting
- ✨ Clean metadata embedding in PNG (individual fields, no JSON blobs)
- ✨ Thumbnail generation for quick previews (512x512)
- 🐛 Fixed duplicate metadata in PNG files
- 🐛 Fixed .gitignore for PyTorch checkpoint files
- 📚 Comprehensive documentation with usage examples

### v0.1.0 (2025-01-26)

- Initial development release
- FLUX.2-dev integration
- Auto-unload functionality (MCP mode)
- Four MCP tools (generate, unload, status, set_timeout)
- CLI tool with interactive mode (`flux` command)
- Shared architecture between CLI and MCP server
