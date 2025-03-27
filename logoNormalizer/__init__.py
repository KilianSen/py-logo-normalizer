import typing

import numpy
import cv2

from logoNormalizer.merge import merge


class Image:
    image: cv2.Mat
    _caching: bool = True

    def __init__(self, im_mat: cv2.Mat, caching: bool = True):
        self._caching = caching
        if im_mat.shape[2] == 3:
            self.image = cv2.cvtColor(im_mat, cv2.COLOR_BGR2BGRA)
        else:
            self.image = im_mat

        aspect_ratio = self.image.shape[0] / self.image.shape[1]
        max_pixels = 1920*1080/4 # this is an arbitrary number, you can change it to whatever you want

        # clamp max pixels, while preserving aspect ratio
        if self.image.shape[0] * self.image.shape[1] > max_pixels:
            self.image = cv2.resize(self.image, (int(numpy.sqrt(max_pixels / aspect_ratio)), int(numpy.sqrt(max_pixels / aspect_ratio))))

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return 0, 0, self.image.shape[1], self.image.shape[0]

    _vb = None
    @property
    def visual_bounds(self) -> tuple[int, int, int, int]:
        if self._vb is not None and self._caching:
            return self._vb
        # return the bounds of the image that contain the visual content
        # the image might have a transparent background, so we need to find the bounds of the visual content
        # this is useful for cropping the image to the visual content

        contours = self.contours

        # max contour
        contour = merge(contours)

        # get the bounding rectangle of the contour
        x, y, w, h = cv2.boundingRect(contour)

        return x, y, w, h

    _vp = None
    @property
    def visual_percentage(self) -> float:
        if self._vp is not None and self._caching:
            return self._vp
        area_total = self.image.shape[0] * self.image.shape[1]
        area_visual = self.visual_bounds[2] * self.visual_bounds[3]

        return area_visual/ area_total

    _fp = None
    @property
    def foreground_percentage(self) -> float:
        if self._fp is not None and self._caching:
            return self._fp
        contours = self.contours

        mask = numpy.zeros(self.image.shape[:2], dtype=numpy.uint8)
        cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)

        area_total = self.image.shape[0] * self.image.shape[1]
        area_visual = cv2.countNonZero(mask)

        return area_visual / area_total

    _cnt = None
    @property
    def contours(self) -> typing.Sequence[cv2.Mat | numpy.ndarray[typing.Any, numpy.dtype[typing.Any]]]:
        if self._cnt is not None and self._caching:
            return self._cnt
        # convert the image to grayscale
        image = cv2.Canny(self.image, 100, 200)
        # find the contours of the image
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    _colors = None
    @property
    def colors(self) -> list:
        if self._colors is not None and self._caching:
            return self._colors
        colors, counts = numpy.unique(self.image.reshape(-1, self.image.shape[2]), axis=0, return_counts=True)
        return sorted(zip(colors, counts), key=lambda x: x[1], reverse=True)

    _bg_colors = None
    @property
    def background_colors(self) -> list[tuple[typing.Any, typing.Any]]:
        if self._bg_colors is not None and self._caching:
            return self._bg_colors
        mask = numpy.zeros(self.image.shape[:2], dtype=numpy.uint8)
        contours = self.contours
        cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)

        background_pixels = self.image[mask == 0]
        unique_colors, counts = numpy.unique(background_pixels.reshape(-1, self.image.shape[2]), axis=0, return_counts=True)

        sorted_colors = sorted(zip(unique_colors, counts), key=lambda x: x[1], reverse=True)

        return sorted_colors

    @property
    def strict_background_colors(self) -> list[list[int]]:
        # returns colors if they are not in the colors
        c = [list(c[0]) for c in self.colors]
        bc =[list(bc[0]) for bc in self.background_colors]

        return [color for color in bc if color not in c]

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
        mask = numpy.all(numpy.abs(blurred_image - color) <= margin, axis=-1)
        s.image[mask] = new_color

        s.invalidate_caches()
        return s

    def extend(self, l, r, t, b, fill) -> 'Image':

        self.image = cv2.copyMakeBorder(self.image, t, b, l, r, cv2.BORDER_CONSTANT, value=[int(x) for x in list(fill)])
        self.invalidate_caches()
        return self

    def resize(self, size) -> 'Image':
        self.image = cv2.resize(self.image, size)
        self.invalidate_caches()
        return self

    def invalidate_caches(self):
        self._vb = None
        self._vp = None
        self._fp = None
        self._cnt = None
        self._colors = None
        self._bg_colors = None

    def morph_to_percentage(self, target_p: float, strict: bool = True, cycle_callback: typing.Callable[[int,],None] = None) -> 'Image':
        cntr = 0
        while (self.visual_percentage > target_p or self.foreground_percentage > target_p) \
                if strict else (self.visual_percentage > target_p and self.foreground_percentage > target_p):
            self.extend(1, 1, 1, 1, (255, 255, 255, 0))
            cntr += 1
            if cycle_callback is not None:
                cycle_callback(cntr)
        return self

    def strip_background(self, fill: list[int] = None, strict: bool = False, limit: int = None) -> 'Image':
        if fill is None:
            fill = self.background_colors[0][0]
        if fill is None:
            fill = [0, 0, 0, 0]

        for color in self.background_colors[:limit] if not strict else self.strict_background_colors[:limit]:
            self.strip_color(color[0], fill, 10)
        return self

    def make_rectangular(self, fill: list[int] = None) -> 'Image':
        if fill is None:
            fill = self.background_colors[0][0]
        if fill is None:
            fill = [0, 0, 0, 0]

        # make the image rectangular (not use visual bounds)
        m_bound = max(self.bounds[2], self.bounds[3])
        d_h, d_w = m_bound - self.bounds[3], (m_bound - self.bounds[2])

        self.extend(d_w // 2, d_w - d_w // 2, d_h // 2, d_h - d_h // 2, fill)

        return self

    def crop_to_visual(self) -> 'Image':
        self.crop(self.visual_bounds)
        return self