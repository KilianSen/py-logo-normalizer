import time
import typing
from collections.abc import Callable
from dataclasses import dataclass
import os
import pathlib
from random import randint

import cv2
from logoNormalizer import Image
from PIL import Image as PILImage


@dataclass
class ImageProcessingOptions:
    file: str
    percentage: float
    resolution: tuple[int, int]
    output_dir: str
    format: str
    strict: bool
    dev_caching: bool

@dataclass
class Status:
    file: str
    visual_percentage: str
    foreground_percentage: str
    output_path: str
    status: str
    step_message: str

def process_file(options: ImageProcessingOptions, status_callback: Callable[[Status,], None]) -> Status:
    """
    Process an image file with the given options
    :param status_callback:
    :param options:  for processing the image
    :return: Status of the processing
    """
    st = Status(file=options.file, visual_percentage="N/A", foreground_percentage="N/A", output_path="N/A", status="N/A", step_message="N/A")
    def update_status(key, value):
        setattr(st, key, value)
        if status_callback:
            status_callback(st)

    def update_vp_fp(im: Image):
        update_status("visual_percentage", f"{im.visual_percentage:.2f}")
        update_status("foreground_percentage", f"{im.foreground_percentage:.2f}")

    try:
        update_status("status", "[blue]Processing[/blue]")
        update_status("step_message", "Loading image")
        im = Image(cv2.imread(options.file, cv2.IMREAD_UNCHANGED), options.dev_caching)
        update_status("step_message", "Cropping to visual content")
        update_vp_fp(im)
        im.crop_to_visual()
        update_status("step_message", "Stripping background")
        im.strip_background(strict=options.strict, fill=[0, 0, 0, 0])
        update_status("step_message", "Making rectangular")
        im.make_rectangular(fill=[0, 0, 0, 0])
        update_vp_fp(im)
        update_status("step_message", "Morphing to percentage")
        im.morph_to_percentage(options.percentage, strict=options.strict, cycle_callback=lambda x: update_vp_fp(im))
        update_status("step_message", "Stripping background")
        im.strip_background(strict=options.strict, fill=[0, 0, 0, 0])
        update_status("step_message", "Resizing to final resolution")
        im.resize(options.resolution)
        image = im.image
        update_status("step_message", "Writing output")
        output_path = os.path.join(options.output_dir, pathlib.Path(options.file).stem + "." + options.format)
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        PILImage.fromarray(image).save(output_path, format=options.format)
        update_status("output_path", output_path)
        update_status("step_message", "")

        time.sleep(randint(1,5))

        update_status("status", "[green]Completed[/green]")

        return st
    except Exception as e:
        update_status("status", f"[red]{str(e)}[/red]")
        return st