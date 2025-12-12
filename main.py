import lib
import random
import os

SEED_MIN = -1000
SEED_MAX = 1000
SIZE_MULTIPLIER = 2
OUTPUT_FN = "output.png"



def main():
    terrains = [
    {
        "name": "Ocean",
        "level": 100,
        "base": [119, 191, 255]},
    {   
        "name": "Beach",
        "level":134,
        "base": [234, 242, 119]},
    {
        "name": "Grassland",
        "level": 190,
        "variation": 32,
        "base": [37, 189, 57]},
    {
        "name": "Mountains",
        "level": 210,
        "variation": 16,
        "base": [89, 89, 89]
    },
    {
        "name": "Snow",
        "level": 256,
        "base": [255, 255, 255]
    }
    ]
    
    w = 1024
    h = 1024
    final_w = w * SIZE_MULTIPLIER
    final_h = h * SIZE_MULTIPLIER

    scale=1.0
    octaves=8
    pixelation_levels=256
    variation=255
    
    os.makedirs("steps", exist_ok=True)

    nmap = lib.generate_noise_map(w, h, scale=scale, pixelation_levels=pixelation_levels, octaves=octaves, persistence=0.5, seed=random.randint(SEED_MIN, SEED_MAX), lacunarity=2.0)
    img = lib.create_image(w, h, (0, 0, 0))
    step = 0
    for y in range(nmap.shape[0]):
        for x in range(nmap.shape[1]):
            step += 1
            value = lib.noise_color(int(nmap[y, x] * 255), variation=variation, terrains=terrains)
            print(f"Step {step}: {x}, {y} -> {value}")
            img = lib.draw_pixel(img, x, y, value)

    img_final = lib.scale_image(img, final_w, final_h)
    img_final.save(OUTPUT_FN)



if __name__ == "__main__":
    main()
