import rich_click as click
from rich.console import Console

from logoNormalizer.cli.cli_group import cli
from logoNormalizer.new_image_processing import ImageProcessingOptions, process_file


@cli.command()
@click.argument("file", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True))
@click.argument("percentage", type=float, default=0.2)
@click.argument("resolution", type=int, nargs=2, default=(512, 512))
@click.argument("output_dir",
                type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True, resolve_path=True),
                default="./")
@click.option("--format", type=str, default="png")
@click.option("--strict", type=bool, default=True)
@click.option("--dev-caching", type=bool, default=True)
def file(file, percentage, resolution, output_dir, format, strict, dev_caching):
    """
    Process a single image file.
    """
    console = Console()

    options = ImageProcessingOptions(
        file=file,
        percentage=percentage,
        resolution=resolution,
        output_dir=output_dir,
        format=format,
        strict=strict,
        dev_caching=dev_caching
    )

    with console.status("[bold blue]Processing image...") as status:
        result = process_file(options, status_callback=lambda st: status.update(
            f"[bold blue]Processing image: {st.step_message}"))

    if "Error" in result.status:
        console.print(f"[red]Error processing {file}: {result.status}[/red]")
    else:
        console.print(f"[green]Successfully processed {file} and saved to {result.output_path}[/green]")
