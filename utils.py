import colorsys
import random

def hue_shifted_color(from_color, shift_range=0.1):
        # Convert to HSV, shift hue, convert back
        r, g, b = from_color
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        h = (h + random.uniform(-shift_range, shift_range)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))

def sanitize_color(color, fallback=(255, 0, 0)):
        if (
            isinstance(color, tuple) and
            len(color) == 3 and
            all(isinstance(c, (int, float)) and 0 <= c <= 255 for c in color)
        ):
            return tuple(int(c) for c in color)
        return fallback