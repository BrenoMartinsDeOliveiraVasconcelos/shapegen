import lib
import random
import os

SEED_MIN = 1
SEED_MAX = 10000
SIZE_MULTIPLIER = 2


def main():
    w = 512
    h = 512
    final_w = w * SIZE_MULTIPLIER
    final_h = h * SIZE_MULTIPLIER
    
    os.makedirs("steps", exist_ok=True)

    nmap = lib.generate_noise_map(w, h, scale=1.0, pixelation_levels=256, octaves=8, persistence=0.5, seed=random.randint(SEED_MIN, SEED_MAX), lacunarity=2.0)
    img = lib.create_image(w, h, (0, 0, 0))
    step = 0
    for y in range(nmap.shape[0]):
        for x in range(nmap.shape[1]):
            step += 1
            value = lib.noise_color(int(nmap[y, x] * 255))
            print(f"Step {step}: {x}, {y} -> {value}")
            img = lib.draw_pixel(img, x, y, value)

    img_final = lib.scale_image(img, final_w, final_h)
    img_final.save("final_image.png")



if __name__ == "__main__":
    main()
