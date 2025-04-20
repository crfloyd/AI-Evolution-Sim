import colorsys

def hue_shifted_color(hue, saturation=1.0, value=1.0):
    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
    return int(r * 255), int(g * 255), int(b * 255)