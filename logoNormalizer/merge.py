import typing
import cv2
import numpy


def merge(contours: typing.Sequence[cv2.Mat]) -> cv2.Mat:
    s_x, m_x = None, None
    s_y, m_y = None, None

    for contour in contours:
        for point in contour:
            if s_x is None or point[0][0] < s_x:
                s_x = point[0][0]
            if m_x is None or point[0][0] > m_x:
                m_x = point[0][0]
            if s_y is None or point[0][1] < s_y:
                s_y = point[0][1]
            if m_y is None or point[0][1] > m_y:
                m_y = point[0][1]

    return cv2.Mat(numpy.array([[[s_x, s_y]], [[m_x, s_y]], [[m_x, m_y]], [[s_x, m_y]]]))
