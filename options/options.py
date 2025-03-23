import enum

class ReColorOptions:
    class Modes(enum.Enum):
        MONO_Provided_Color = 0
        MONO_Derived_Color = 1
        MONO_Black = 2

    provided_color: (int, int, int, int)

class BackgroundRemovalOptions:
    class Modes(enum.Enum):
        WHITE = 0
        BLACK = 1
        TRANSPARENT = 2

    mode: Modes
    replace_color: (int, int, int, int)
    threshold: float

class Options:
    def __init__(self):
        self.color_limit = None

    target_resolution: (int, int)
    target_visual_percentage: float

    remove_background: BackgroundRemovalOptions
    recolor: ReColorOptions
