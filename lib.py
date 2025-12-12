import PIL
from PIL import Image, ImageDraw
import numpy as np
from noise import snoise2

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
    total_pixels = width * height
    step = 0
    seed_divisor = 100
    for i in range(height):
        for j in range(width):
            step += 1
            
            print(f"[{percent(step, total_pixels):.2f}%] Generating noise map {step}/{total_pixels}: ({j}, {i})")
            noise_map[i, j] = snoise2(yv[i, j], xv[i, j],
                                      octaves=octaves,
                                      persistence=persistence,
                                      lacunarity=lacunarity,
                                      base=seed/seed_divisor)
    
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


def noise_color(value: int, variation: int, terrains: list[dict]) -> tuple:
    prev_level = 0
    
    for t in terrains:
        level = t["level"]
        
        if value < level:
            base_color = t["base"]
            variation_count = max(1, variation)
            
            band_size = level - prev_level
            
            value_in_band = value - prev_level
            pct = value_in_band / band_size if band_size > 0 else 0
            
            current_step = int(pct * variation_count)
            
            brightness = 0.8 + (0.4 * (current_step / variation_count))
            color = change_brightness(base_color, brightness)
            
            return color

        prev_level = level

    return (255, 255, 255)

def change_brightness(rgb: tuple, brightness: float) -> tuple:
    rgb_adjusted = []

    for c in rgb:
        new_val = int(max(0, min(255, c * brightness)))
        rgb_adjusted.append(new_val)

    return tuple(rgb_adjusted)


def percent(a, b)->float:
    return (a / b) * 100