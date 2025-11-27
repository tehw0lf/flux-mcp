# FLUX MCP Server & CLI

A Model Context Protocol (MCP) server and command-line tool for generating images using FLUX.2-dev with automatic model unloading to save VRAM and power.

## Features

- 🎨 **High-Quality Image Generation** - Uses FLUX.2-dev for state-of-the-art image synthesis
- ⚡ **Smart VRAM Management** - Automatically selects best strategy based on available VRAM
- 🔄 **Auto-Unload** - Automatically unloads model after configurable inactivity period (MCP mode)
- 💾 **Memory Efficient** - Model CPU offload for 16GB GPUs, full GPU mode for 24GB+
- 🎲 **Reproducible** - Seed-based generation for consistent results
- 📊 **Status Monitoring** - Check model status and VRAM usage
- 🔧 **Runtime Configuration** - Adjust timeout without restarting
- 🖥️ **Dual Interface** - Use via MCP-compatible applications or command-line (CLI)

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
# See "MCP Server Registration" section below for full details

# 4. Generate your first image (CLI mode)
flux generate "a beautiful sunset over mountains"

# Or use via MCP client (e.g., Claude Desktop)
# Just ask: "Generate an image of a beautiful sunset over mountains"
```

For detailed setup and configuration, see the sections below.

## Requirements

- Python 3.10+
- NVIDIA GPU with 12GB+ VRAM (16GB recommended, 24GB+ for maximum speed)
- CUDA toolkit installed
- PyTorch with CUDA support

**VRAM Modes:**
- **24GB+** - Full GPU mode (fastest, ~2-4 minutes for 1024x1024)
- **16GB** - Model CPU offload mode (balanced, ~5-10 minutes for 1024x1024)
- **12GB** - Model CPU offload mode (slower, may need reduced resolution)

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

### Configuration Options

Edit `.env` to customize:

```bash
# Auto-unload timeout in seconds (default: 300 = 5 minutes)
FLUX_UNLOAD_TIMEOUT=300

# Output directory for generated images
FLUX_OUTPUT_DIR=/path/to/flux_output

# Optional: Custom HuggingFace cache directory
# FLUX_MODEL_CACHE=/path/to/cache

# Default generation parameters (adjust for faster previews)
# FLUX_DEFAULT_STEPS=50        # Default: 50 (high quality), use 28 for faster
# FLUX_DEFAULT_GUIDANCE=7.5    # Default: 7.5 (strong adherence), use 3.0-4.0 for looser
```

## MCP Server Registration

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

Generated images are saved with metadata:

- **Image:** `flux_YYYYMMDD_HHMMSS_SEED.png`
- **Metadata:** `flux_YYYYMMDD_HHMMSS_SEED.json`

Metadata JSON contains:
```json
{
  "prompt": "your prompt here",
  "seed": 42,
  "steps": 28,
  "guidance_scale": 3.5,
  "width": 1024,
  "height": 1024,
  "model": "black-forest-labs/FLUX.2-dev",
  "generation_time_seconds": 15.3,
  "timestamp": "2025-01-26T12:34:56"
}
```

### CLI vs MCP Server

**CLI Mode:**
- ✓ Completely offline and private (no MCP client needed)
- ✓ Direct control from terminal
- ✓ Batch generation with interactive mode
- ✓ No auto-unload (process terminates after generation)
- ✓ Saves metadata JSON files
- ✓ Rich terminal UI with progress bars

**MCP Server Mode:**
- ✓ Integrated with MCP-compatible applications (like Claude Desktop)
- ✓ Natural language interface
- ✓ Auto-unload after timeout (saves power)
- ✓ Persistent background process
- ✓ Access from conversational AI interfaces

Both modes share the same configuration, model cache, and output directory.

## MCP Server Tools

The following tools are available when using this server with any MCP-compatible client. Examples below show usage with Claude Desktop:

### 1. `generate_image`

Generate an image from a text prompt.

**Parameters:**
- `prompt` (required): Text description of the image
- `steps` (optional): Number of inference steps (default: 50, range: 20-100)
- `guidance_scale` (optional): Guidance scale (default: 7.5, range: 1.0-10.0)
- `width` (optional): Image width in pixels (default: 1024, range: 256-2048)
- `height` (optional): Image height in pixels (default: 1024, range: 256-2048)
- `seed` (optional): Random seed for reproducibility (random if not provided)

**Example Usage (natural language with MCP client):**
```
Generate an image of a futuristic cyberpunk city at sunset with neon lights
```

```
Generate an image with seed 42 of a serene mountain landscape with steps=30
```

### 2. `unload_model`

Immediately unload the FLUX model from GPU memory.

**Example Usage:**
```
Unload the FLUX model to free up VRAM
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

### 4. `set_timeout`

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

## Usage Examples

These examples demonstrate using the MCP server with conversational AI clients (like Claude Desktop):

### Basic Image Generation

```
Generate an image: "A majestic dragon flying over a medieval castle"
```

The server will:
1. Load the FLUX model (if not already loaded)
2. Generate the image
3. Save it to the output directory as `YYYYMMDD_HHMMSS_{seed}.png`
4. Return the file path, seed, and generation settings
5. Schedule auto-unload after 5 minutes (default)

### Reproducible Generation

To generate the same image again, use the seed from a previous generation:

```
Generate an image with seed 12345: "A cute robot playing with a kitten"
```

### Custom Parameters

```
Generate a portrait with steps=40, guidance_scale=7.5, width=768, height=1024:
"Professional headshot of a business executive"
```

### Memory Management

Check current status:
```
What's the FLUX model status?
```

Manually unload to free VRAM:
```
Unload the FLUX model
```

Adjust auto-unload timeout:
```
Set FLUX timeout to 10 minutes
```

## How It Works

### Smart VRAM Detection

On model load, the server:

1. **Detects total VRAM** available on your GPU
2. **Selects optimal mode** automatically:
   - **24GB+**: Full GPU mode (all components stay on GPU)
   - **12-24GB**: Model CPU offload mode (components moved between CPU/GPU as needed)
3. **Logs the decision** so you know which mode is active

**Model CPU Offload** moves entire model components (text encoder, transformer, VAE) to CPU when not actively being used. This is **much faster** than sequential CPU offload (which moves individual submodules).

For GPUs with <24GB VRAM, the server also enables:
- **VAE Slicing**: Processes VAE decoding in smaller chunks
- **Attention Slicing**: Computes attention in smaller steps

These combined optimizations fit FLUX.2-dev in 12-16GB VRAM.

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

- **Smart mode selection** based on detected VRAM (24GB+: full GPU, <24GB: model offload)
- **bfloat16 precision** instead of float32 (saves ~50% VRAM)
- **Model CPU offload** for <24GB GPUs (only active component stays on GPU)
- **VAE slicing** for <24GB GPUs (processes VAE decoding in chunks)
- **Attention slicing** for <24GB GPUs (computes attention in smaller steps)
- **Explicit cache clearing** when unloading
- **Threading** for non-blocking auto-unload
- **Lock-based synchronization** for thread-safe operation

### Output Files

Generated images are saved as:
```
{FLUX_OUTPUT_DIR}/{timestamp}_{seed}.png
```

Example: `20250126_143052_42.png`

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

## Advanced Configuration

### Custom Model Cache

To share the model cache across multiple projects or save space:

```bash
# In .env
FLUX_MODEL_CACHE=/mnt/data/huggingface/cache
```

### Disable Auto-Unload

To keep the model loaded permanently (uses more power but faster):

```bash
# In .env
FLUX_UNLOAD_TIMEOUT=0
```

Or at runtime:
```
Set FLUX timeout to 0
```

### Logging

The server logs to stderr. To capture logs:

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

## Performance Tips

### Optimal Settings by GPU VRAM

**RTX 4090 / A6000 (24GB+)**
- **Resolution**: Up to 1536x1536 comfortably
- **Mode**: Full GPU (automatic)
- **Steps**: 50 for high quality, 28 for faster previews
- **Guidance**: 7.5 (default) or 3.0-4.0 for looser results
- **Expected time**: ~2-4 minutes for 1024x1024@50 steps

**RTX 4070 Ti Super / 3090 (16GB-24GB)**
- **Resolution**: Up to 1024x1024 comfortably
- **Mode**: Sequential CPU offload (automatic for 16GB)
- **Steps**: 50 for high quality (default), 28 for faster (~25 min)
- **Guidance**: 7.5 (default) recommended
- **Expected time**: ~37 minutes for 1024x1024@50 steps
- **Tip**: Set `FLUX_DEFAULT_STEPS=28` in `.env` for faster defaults

**RTX 3060 / 4060 Ti (12GB-16GB)**
- **Resolution**: 768x768 recommended for reliability
- **Mode**: Sequential CPU offload (automatic)
- **Steps**: 28-35 recommended
- **Expected time**: ~20-30 minutes for 768x768@28 steps

**All GPUs:**
- **Guidance Scale**: 7.5 (default, strong adherence) or 3.0-4.0 (looser/creative)
- **Batch size**: 1 (model doesn't support batching)
- **Timeout**: 300s for occasional use, 600s for active sessions

### Generation Time Expectations

**Full GPU Mode (24GB+ VRAM):**
- **1024x1024, 50 steps, guidance 7.5**: ~2-4 minutes
- **1024x1024, 28 steps**: ~1-2 minutes
- **First generation**: +15-30 seconds for model loading

**Sequential CPU Offload (16GB VRAM - RTX 4070 Ti Super):**
- **1024x1024, 50 steps, guidance 7.5**: ~37 minutes (~45 sec/step)
- **1024x1024, 28 steps**: ~25 minutes (~30 sec/step)
- **768x768, 28 steps**: ~18-22 minutes
- **First generation**: +2-3 seconds for model loading
- **Optimization**: Use `FLUX_DEFAULT_STEPS=28` for 30% faster generation

## Technical Details

### Architecture

```
flux-mcp/
├── src/flux_mcp/
│   ├── __init__.py       # Package metadata
│   ├── config.py         # Environment configuration (shared)
│   ├── generator.py      # FluxGenerator class (shared)
│   ├── server.py         # MCP server (tool handlers)
│   └── cli.py            # CLI tool
├── pyproject.toml        # Project dependencies
├── .env                  # Local configuration
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

### v0.1.0 (2025-01-26)

- Initial release
- FLUX.2-dev integration
- Auto-unload functionality (MCP mode)
- Four MCP tools (generate, unload, status, set_timeout)
- CLI tool with interactive mode (`flux` command)
- Shared architecture between CLI and MCP server
- Comprehensive documentation with CLI and MCP usage examples
