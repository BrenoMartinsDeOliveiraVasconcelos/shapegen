import lib
import random
import os

SEED_MIN = -10000
SEED_MAX = 10000
SIZE_MULTIPLIER = 32


def main():
    w = 32
    h = 32
    final_w = w * SIZE_MULTIPLIER
    final_h = h * SIZE_MULTIPLIER
    
    os.makedirs("steps", exist_ok=True)

    nmap = lib.generate_noise_map(w, h, scale=3.0, octaves=1, seed=random.randint(SEED_MIN, SEED_MAX), lacunarity=0.5, persistence=0.5, pixelation_levels=8)
    img = lib.create_image(w, h, (0, 0, 0))
    step = 0
    for y in range(nmap.shape[0]):
        for x in range(nmap.shape[1]):
            step += 1
            value = lib.noise_color(int(nmap[y, x] * 255))
            img = lib.draw_pixel(img, x, y, value)
            img_r = lib.scale_image(img, final_w, final_h)
            img_r.save(f"steps/step_{step:04d}.png")

    img_final = lib.scale_image(img, final_w, final_h)
    img_final.save("final_image.png")



if __name__ == "__main__":
    main()
