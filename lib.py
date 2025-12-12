import PIL
from PIL import Image, ImageDraw
import numpy as np
from noise import pnoise2
import json

def create_image(width, height, color):
    """Create a new image with the specified width, height, and color."""
    return Image.new("RGB", (width, height), color)


def draw_pixel(image, x, y, color):
    """Draw a pixel on the image at the specified coordinates."""
    draw = ImageDraw.Draw(image)
    draw.point((x, y), fill=color)
    return image

def generate_noise_map(width, height, scale=100.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=0, pixelation_levels=16):
    x = np.linspace(0, scale, width, endpoint=False)
    y = np.linspace(0, scale, height, endpoint=False)
    
    xv, yv = np.meshgrid(x, y)
    
    noise_map = np.zeros((height, width))
    
    for i in range(height):
        for j in range(width):
            noise_map[i, j] = pnoise2(yv[i, j], xv[i, j],
                                      octaves=octaves,
                                      persistence=persistence,
                                      lacunarity=lacunarity,
                                      base=seed)
    
    noise_min = noise_map.min()
    noise_max = noise_map.max()
    
    if noise_max - noise_min > 0:
        noise_map = (noise_map - noise_min) / (noise_max - noise_min)
    
    # Pixelate the noise map
    noise_normalized = (noise_map - noise_map.min()) / (noise_map.max() - noise_map.min())
    noise_quantized = np.floor(noise_normalized * pixelation_levels) / pixelation_levels
    return noise_quantized


def scale_image(image, final_width, final_height):
    """Scale without interpolation to preserve pixelated look."""
    return image.resize((final_width, final_height), resample=PIL.Image.NEAREST)


def noise_color(value: int) -> tuple:
    terrains = json.load(open("terrains.json"))

    index = 0
    for t in terrains:
        level = t["level"]
        if value < level:
            variation = t["variation"]
            base_bright = 1.0
            terrain_size = terrains[index+1]["level"] - level if index+1 < len(terrains) else 255 - level
            bright_factor = base_bright / variation
            terrain_layer_steps = int(terrain_size / variation)
            
            terrain_layer_value = value-terrains[index-1]["level"] if index > 0 else value

            part = 1
            for val in range(0, terrain_size, terrain_layer_steps):
                print(val)
                if terrain_layer_value <= val:
                    part += 1

            brightness = base_bright - (bright_factor * part)

            return change_brightness((c for c in t["base"]), brightness)

        index += 1
            

def change_brightness(rgb: tuple, brightness: float) -> tuple:
    rgb_list = [code for code in rgb]
    rgb_adjusted = []

    for c in rgb_list:
        rgb_adjusted.append(max(0, min(255, c * brightness)))
    

    return tuple(int(c) for c in rgb_adjusted)
