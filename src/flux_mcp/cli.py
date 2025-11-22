"""CLI tool for FLUX image generation."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
import torch
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import config
from .generator import FluxGenerator

console = Console()

# Disable noisy logging for CLI
logging.getLogger("diffusers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)


def validate_dimensions(ctx, param, value):
    """Validate that dimensions are multiples of 8."""
    if value % 8 != 0:
        raise click.BadParameter("must be a multiple of 8")
    if value < 256 or value > 2048:
        raise click.BadParameter("must be between 256 and 2048")
    return value


@click.group()
@click.version_option(version="0.1.0", prog_name="flux")
def cli():
    """FLUX.1-dev CLI - Generate images locally with FLUX."""
    pass


@cli.command()
@click.argument("prompt", required=False)
@click.option(
    "--steps",
    "-s",
    default=28,
    type=int,
    help="Number of inference steps (default: 28)",
)
@click.option(
    "--guidance",
    "-g",
    default=3.5,
    type=float,
    help="Guidance scale (default: 3.5)",
)
@click.option(
    "--width",
    "-w",
    default=1024,
    type=int,
    callback=validate_dimensions,
    help="Image width in pixels (must be multiple of 8)",
)
@click.option(
    "--height",
    "-h",
    default=1024,
    type=int,
    callback=validate_dimensions,
    help="Image height in pixels (must be multiple of 8)",
)
@click.option(
    "--seed",
    type=int,
    help="Random seed for reproducibility",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Custom output path (default: auto-generated)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    help="Override output directory",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode with prompts",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output with debug info",
)
def generate(
    prompt, steps, guidance, width, height, seed, output, output_dir, interactive, verbose
):
    """Generate an image from a text prompt.

    Examples:

        flux generate "a beautiful sunset over mountains"

        flux generate "portrait of a cat" --steps 35 --seed 42

        flux generate --interactive
    """
    # Set logging level
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    # Override output directory if specified
    if output_dir:
        config.output_dir = Path(output_dir)
        config.output_dir.mkdir(parents=True, exist_ok=True)

    # Check CUDA availability
    if not torch.cuda.is_available():
        console.print("[red]✗ CUDA not available. GPU required for FLUX.[/red]")
        console.print("\nPlease ensure:")
        console.print("  • NVIDIA GPU is installed")
        console.print("  • CUDA toolkit is installed")
        console.print("  • PyTorch with CUDA support is installed")
        sys.exit(1)

    # Interactive mode
    if interactive:
        _interactive_mode()
        return

    # Validate prompt
    if not prompt:
        console.print("[red]✗ Error: Prompt is required[/red]")
        console.print('\nUsage: flux generate "your prompt here"')
        console.print("   or: flux generate --interactive")
        sys.exit(1)

    # Generate image
    _generate_image(
        prompt=prompt,
        steps=steps,
        guidance=guidance,
        width=width,
        height=height,
        seed=seed,
        output_path=output,
        verbose=verbose,
    )


def _generate_image(
    prompt, steps, guidance, width, height, seed, output_path, verbose, generator=None
):
    """Internal function to generate a single image."""
    # Create generator if not provided (for single-shot mode)
    if generator is None:
        generator = FluxGenerator(auto_unload=False)

    try:
        # Load model with progress indicator
        if generator.pipeline is None:
            with console.status("[bold green]Loading FLUX model...", spinner="dots"):
                generator._load_model()
            console.print("✓ Model loaded\n")

        # Generate image with progress
        console.print("[bold cyan]🎨 Generating image...[/bold cyan]")
        if verbose:
            console.print(f"  Prompt: {prompt}")
            console.print(f"  Steps: {steps}, Guidance: {guidance}")
            console.print(f"  Resolution: {width}x{height}")
            if seed:
                console.print(f"  Seed: {seed}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            _task = progress.add_task("Generating...", total=None)

            # Generate
            result_path, used_seed, settings, _pil_image = generator.generate(
                prompt=prompt,
                steps=steps,
                guidance_scale=guidance,
                width=width,
                height=height,
                seed=seed,
            )

        # Handle custom output path
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.rename(output_path)
            result_path = output_path

        # Save metadata
        metadata_path = result_path.with_suffix(".json")
        metadata = {
            "prompt": prompt,
            "seed": used_seed,
            "steps": steps,
            "guidance_scale": guidance,
            "width": width,
            "height": height,
            "model": config.model_id,
            "generation_time_seconds": float(settings["generation_time"].rstrip("s")),
            "timestamp": datetime.now().isoformat(),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Success output
        console.print("\n[bold green]✓ Image generated successfully![/bold green]\n")
        console.print(f"  📁 Image: {result_path}")
        console.print(f"  📄 Metadata: {metadata_path}")
        console.print(f"  ⏱️  Generation time: {settings['generation_time']}")
        console.print(f"  🎲 Seed: {used_seed}")

        if not verbose:
            console.print(f"\n[dim]Tip: Use --seed {used_seed} to reproduce this image[/dim]")

    except torch.cuda.OutOfMemoryError:
        console.print("\n[red]✗ Out of VRAM![/red]")
        console.print("\nTry reducing resolution:")
        console.print(f"  flux generate '{prompt}' --width 768 --height 768")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


def _interactive_mode():
    """Interactive mode for batch generation."""
    console.print(
        Panel.fit(
            "🎨 [bold cyan]FLUX Image Generator[/bold cyan] - Interactive Mode\n"
            "[dim]Generate multiple images with the same loaded model[/dim]",
            border_style="cyan",
        )
    )

    # Create generator once for entire session
    generator = FluxGenerator(auto_unload=False)

    while True:
        console.print("\n" + "─" * 60)

        # Get prompt
        prompt = console.input("\n[bold]Enter prompt[/bold] (or 'quit' to exit): ").strip()
        if prompt.lower() in ("quit", "exit", "q"):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not prompt:
            console.print("[yellow]⚠ Prompt cannot be empty[/yellow]")
            continue

        # Get parameters with defaults
        try:
            steps_input = console.input("[bold]Steps[/bold] [dim][28][/dim]: ").strip()
            steps = int(steps_input) if steps_input else 28

            guidance_input = console.input("[bold]Guidance scale[/bold] [dim][3.5][/dim]: ").strip()
            guidance = float(guidance_input) if guidance_input else 3.5

            width_input = console.input("[bold]Width[/bold] [dim][1024][/dim]: ").strip()
            width = int(width_input) if width_input else 1024

            height_input = console.input("[bold]Height[/bold] [dim][1024][/dim]: ").strip()
            height = int(height_input) if height_input else 1024

            seed_input = console.input("[bold]Seed[/bold] [dim](random if empty)[/dim]: ").strip()
            seed = int(seed_input) if seed_input else None

            # Validate dimensions
            if width % 8 != 0 or height % 8 != 0:
                console.print("[red]✗ Width and height must be multiples of 8[/red]")
                continue

            if width < 256 or width > 2048 or height < 256 or height > 2048:
                console.print("[red]✗ Dimensions must be between 256 and 2048[/red]")
                continue

        except ValueError as e:
            console.print(f"[red]✗ Invalid input: {e}[/red]")
            continue

        # Generate image
        _generate_image(
            prompt=prompt,
            steps=steps,
            guidance=guidance,
            width=width,
            height=height,
            seed=seed,
            output_path=None,
            verbose=False,
            generator=generator,
        )

        # Ask to continue
        console.print()
        continue_input = (
            console.input("[bold]Generate another image?[/bold] [dim][y/N][/dim]: ").strip().lower()
        )
        if continue_input not in ("y", "yes"):
            console.print("\n[dim]Goodbye![/dim]")
            break


@cli.command()
def status():
    """Show FLUX generator status and system information."""
    table = Table(title="FLUX Generator Status", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    # Model info
    table.add_row("Model", config.model_id)
    table.add_row("Output Directory", str(config.output_dir))

    # CUDA info
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        vram_allocated = torch.cuda.memory_allocated() / (1024**3)
        vram_reserved = torch.cuda.memory_reserved() / (1024**3)

        table.add_row("CUDA Available", "✓ Yes")
        table.add_row("GPU", gpu_name)
        table.add_row("Total VRAM", f"{vram_total:.2f} GB")
        table.add_row("Allocated VRAM", f"{vram_allocated:.2f} GB")
        table.add_row("Reserved VRAM", f"{vram_reserved:.2f} GB")
    else:
        table.add_row("CUDA Available", "[red]✗ No[/red]")

    # Cache info
    if config.model_cache:
        table.add_row("Model Cache", str(config.model_cache))
    else:
        from pathlib import Path

        default_cache = Path.home() / ".cache" / "huggingface" / "hub"
        table.add_row("Model Cache", f"{default_cache} [dim](default)[/dim]")

    console.print(table)


@cli.command()
def config_cmd():
    """Show current configuration."""
    table = Table(title="FLUX Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Variable", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("FLUX_OUTPUT_DIR", str(config.output_dir))
    table.add_row("FLUX_MODEL", config.model_id)
    table.add_row("FLUX_UNLOAD_TIMEOUT", f"{config.unload_timeout}s [dim](MCP only)[/dim]")

    if config.model_cache:
        table.add_row("FLUX_MODEL_CACHE", str(config.model_cache))

    console.print(table)
    console.print("\n[dim]Config file: ~/.config/flux-mcp/.env (if exists)[/dim]")
    console.print(f"[dim]Or: {Path.cwd() / '.env'} (if exists)[/dim]")


@cli.command()
def open_output():
    """Open the output directory in file manager."""
    import subprocess

    output_dir = config.output_dir

    if not output_dir.exists():
        console.print(f"[yellow]⚠ Output directory doesn't exist yet: {output_dir}[/yellow]")
        console.print("[dim]It will be created when you generate your first image.[/dim]")
        return

    try:
        # Linux
        subprocess.run(["xdg-open", str(output_dir)], check=True)
        console.print(f"✓ Opened {output_dir}")
    except FileNotFoundError:
        # macOS
        try:
            subprocess.run(["open", str(output_dir)], check=True)
            console.print(f"✓ Opened {output_dir}")
        except FileNotFoundError:
            # Windows
            try:
                subprocess.run(["explorer", str(output_dir)], check=True)
                console.print(f"✓ Opened {output_dir}")
            except FileNotFoundError:
                console.print("[red]✗ Could not open file manager[/red]")
                console.print(f"\nOutput directory: {output_dir}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Error opening directory: {e}[/red]")


def main():
    """Main entry point for CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/dim]")
        sys.exit(130)


if __name__ == "__main__":
    main()
