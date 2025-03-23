import copy
from functools import lru_cache
from importlib import invalidate_caches
from typing import Any, Sequence

import cv2
import numpy as np
from cv2 import Mat
from numpy import ndarray, dtype

from contours import merge
from options.options import Options

options = Options()

class Image:
    def __init__(self, path):
        self.path = path
        self.image = cv2.imread(path, cv2.IMREAD_COLOR)

        aspect_ratio = self.image.shape[0] / self.image.shape[1]
        max_pixels = 1920*1080/4 # this is an arbirary number, you can change it to whatever you want

        # clamp max pixels, while preserving aspect ratio
        if self.image.shape[0] * self.image.shape[1] > max_pixels:
            print("Resizing input image to ", (int(np.sqrt(max_pixels / aspect_ratio)), int(np.sqrt(max_pixels * aspect_ratio))))
            self.image.resize((int(np.sqrt(max_pixels * aspect_ratio)), int(np.sqrt(max_pixels / aspect_ratio)), 3))
        self.image = self.image


    @property
    def visual_bounds(self) -> (int, int, int, int):
        # return the bounds of the image that contain the visual content
        # the image might have a transparent background, so we need to find the bounds of the visual content
        # this is useful for cropping the image to the visual content

        contours = self.contours

        # max contour
        contour = merge(contours)

        # get the bounding rectangle of the contour
        x, y, w, h = cv2.boundingRect(contour)

        return x, y, w, h

    @property
    def visual_percentage(self) -> float:
        area_total = self.image.shape[0] * self.image.shape[1]
        area_visual = self.visual_bounds[2] * self.visual_bounds[3]

        return area_visual/ area_total

    @property
    def foreground_percentage(self) -> float:
        contours = self.contours

        mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, contours, -1, (255), thickness=cv2.FILLED)

        area_total = self.image.shape[0] * self.image.shape[1]
        area_visual = cv2.countNonZero(mask)

        return area_visual / area_total

    @property
    def contours(self) -> Sequence[Mat | ndarray[Any, dtype[Any]]]:
        # convert the image to grayscale
        image = cv2.Canny(self.image, 100, 200)
        # find the contours of the image
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    @property
    def colors(self) -> tuple:
        colors = np.unique(self.image.reshape(-1, self.image.shape[2]), axis=0, return_counts=True)
        return colors[:options.color_limit]

    @property
    def background_colors(self) -> list[tuple[Any, Any]]:
        mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        contours = self.contours
        cv2.drawContours(mask, contours, -1, (255), thickness=cv2.FILLED)

        background_pixels = self.image[mask == 0]
        unique_colors, counts = np.unique(background_pixels.reshape(-1, self.image.shape[2]), axis=0, return_counts=True)

        sorted_colors = sorted(zip(unique_colors, counts), key=lambda x: x[1], reverse=True)

        return sorted_colors[:options.color_limit]

    def invalidate_caches(self):
        pass

    def crop(self, bounds) -> 'Image':
        s = self

        x, y, w, h = bounds
        s.image = s.image[y:y+h, x:x+w]

        s.invalidate_caches()
        return s

    def strip_color(self, color, new_color, margin, blur=3) -> 'Image':
        s = self
        new_color = new_color[:s.image.shape[2]]  # Ensure new_color has the same number of channels as the image
        blurred_image = cv2.GaussianBlur(s.image, (blur, blur), 0)
        mask = np.all(np.abs(blurred_image - color[0]) <= margin, axis=-1)
        s.image[mask] = new_color

        s.invalidate_caches()
        return s

    def extend(self, l, r, t, b, fill) -> 'Image':
        self.image = cv2.copyMakeBorder(self.image, t, b, l, r, cv2.BORDER_CONSTANT, value=fill)

        self.invalidate_caches()
        return self

    def resize(self, size) -> 'Image':
        self.image = cv2.resize(self.image, size)
        return self

target_p = .2
target_res = (256, 256)

Test = Image("2.png")
Test = Test.crop(Test.visual_bounds)
m_bound = max(Test.visual_bounds[2], Test.visual_bounds[3])
print("Got bounds")
dH, dW = m_bound - Test.visual_bounds[3], (m_bound - Test.visual_bounds[2])
Test = Test.extend(dW//2, dW - dW//2, dH//2, dH - dH//2, (255, 255, 255))
print("Rectangular finish")
cntr= 0
while Test.visual_percentage > target_p or Test.foreground_percentage > target_p:
    Test = Test.extend(1, 1, 1, 1, (255, 255, 255))
    cntr += 1
    print(f"Extension {cntr}, {Test.visual_percentage} {Test.foreground_percentage}", end="\r")
print(Test.visual_percentage, Test.foreground_percentage)

print(123)
Test = Test.strip_color(Test.background_colors[0], (0,0,0,0), 10)

Test = Test.resize(target_res)

cv2.imshow("Test", Test.image)
cv2.waitKey(0)