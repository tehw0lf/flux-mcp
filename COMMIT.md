# Commit Message

```
feat: add Apple Silicon (MPS) support

Auto-detect compute device at startup (CUDA → MPS → CPU). On MPS:
- Load model with float16 instead of bfloat16 (more stable on MPS)
- Skip CPU offload and xFormers (not supported on MPS)
- Use torch.mps.empty_cache() and torch.mps.synchronize()
- Use CPU-based torch.Generator for seed (MPS compatibility)
- Default to FLUX.1-dev (FLUX.2-dev exceeds typical unified memory)

Add psutil as optional dependency ([project.optional-dependencies.mac])
for unified memory reporting on MPS. Install with: uv sync --extra mac

Also fix two pre-existing bugs:
- cli.py: unpack 5 return values from generate() (image_id was missing)
- config.py: call expanduser() on paths so ~ in .env is correctly expanded

No changes to existing CUDA behavior.
```

## Files changed

- `src/flux_mcp/generator.py` — device detection, MPS load/unload/generate/status
- `src/flux_mcp/config.py` — FLUX.1-dev default on MPS, expanduser() on paths
- `src/flux_mcp/cli.py` — device-aware info/error handling, fix 5-value unpack
- `pyproject.toml` — add `[mac]` optional dependency group with psutil
- `README.md` — Mac requirements, Apple Silicon section in troubleshooting
