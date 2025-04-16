import os

import rich_click as click
from rich.console import Console
from rich.live import Live
from rich.table import Table
from logoNormalizer.cli.cli_group import cli
from logoNormalizer.new_image_processing import ImageProcessingOptions, process_file, Status
import multiprocessing

def directory_task_with_ipc(file, percentage, resolution, output_dir, format, strict, dev_caching, status_queue):
    options = ImageProcessingOptions(file=file, percentage=percentage, resolution=resolution, output_dir=output_dir,
                                     format=format, strict=strict, dev_caching=dev_caching)

    def status_callback(status: Status):
        status_queue.put(status)
    result = process_file(options, status_callback)
    status_queue.put(result)  # Ensure the final status is also sent
    return result

@cli.command()
@click.argument("directory", default="", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("percentage", type=float, default=0.2)
@click.argument("resolution", type=int, nargs=2, default=(512, 512))
@click.argument("output_dir",
                type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True, resolve_path=True),
                default=".")
@click.option("--format", type=str, default="png")
@click.option("--strict", type=bool, default=True)
@click.option("--dev-caching", type=bool, default=True)
@click.option("--max-workers", type=int, default=int(multiprocessing.cpu_count() // 4), help="Maximum number of worker processes.")
def directory(directory, percentage, resolution, output_dir, format, strict, dev_caching, max_workers):
    """Process all images in a directory."""
    console = Console()
    files = [os.path.join(directory, f) for f in os.listdir(directory) if
             os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(
                 ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', ".webp"))]

    if not files:
        console.print("[yellow]No images found in directory.[/yellow]")
        return

    file_statuses = {
        file: Status(file=file, visual_percentage="N/A", foreground_percentage="N/A", output_path="N/A", status="Waiting",
                     step_message="N/A") for file in files
    }

    def generate_table():
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No", justify="right")
        table.add_column("File", overflow="ellipsis", no_wrap=True, max_width=40)
        table.add_column("Visual %", justify="right")
        table.add_column("Foreground %", justify="right")
        table.add_column("Output", justify="right", overflow="ellipsis", no_wrap=True, max_width=40, width=40)
        table.add_column("Step Message", justify="left", overflow="ellipsis", no_wrap=True, max_width=20, width=20)
        table.add_column("Status", justify="center")
        cntr = 0
        for file, status in file_statuses.items():
            table.add_row(
                str(cntr),
                file,
                status.visual_percentage,
                status.foreground_percentage,
                status.output_path,
                status.step_message,
                status.status
            )
            cntr += 1
        return table

    status_queue = multiprocessing.Queue()

    with Live(generate_table(), console=console, refresh_per_second=10) as live:
        processes = []
        for file in files:
            p = multiprocessing.Process(target=directory_task_with_ipc, args=(
                file, percentage, resolution, output_dir, format, strict, dev_caching, status_queue))
            processes.append(p)

        finished_count = 0

        while finished_count < len(processes):
            while not status_queue.empty():
                status = status_queue.get(timeout=25)
                file_statuses[status.file] = status
                live.update(generate_table())
            active_count = sum(p.is_alive() for p in processes)
            finished_count = sum(p.exitcode is not None for p in processes)

            if active_count < max_workers and finished_count < len(processes):
                for p in processes:
                    if not p.is_alive() and p.exitcode is None:
                        p.start()
                        active_count += 1
                        break