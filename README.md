# shapegen

Terrain & Noise Map Generator (GUI)

shapegen is a small Python project that generates pixelated terrain maps using procedural noise. It provides a Qt-based GUI to configure generation parameters and terrain bands (colors/levels), then renders and saves the result as an image.

# Features
- Interactive PyQt6 GUI for parameter tuning (size, scale, octaves, pixelation, seed).
- Customizable terrain bands with names, levels and base colors.
- Procedural noise generation using simplex/perlin noise (via the `noise` package).
- Pixel-art friendly scaling (nearest-neighbor) to preserve blocky look.

# Requirements
**Python**
- Python 3.10+ (or your system Python that supports the dependencies)
- Pillow
- numpy
- noise
- PyQt6

**System libraries**

Linux: libqt6, libpython3-dev, xcb

**Minimum specs**
| Resolution | CPU | RAM |
|---|---|---|
| 64x64 | Dual core | 256 MB |
| 128x128 | Dual core | 256 MB |
| 256x256 | Dual core | 256 MB |
| 512x512 | Dual core | 256 MB |
| 1024x1024 | Dual core | 512 MB |
| 2048x2048 | Dual core | 1 GB |
| 4096x4096 | Dual core | 4 GB |
| 8192x8192 | Dual core | 12 GB |

*Tested with defaults


# Run
* Open a terminal in the project directory (where `gui.py` and `lib.py` live).
* Run:

```bash
python gui.py
```

* Use the left panel to adjust width, height, scale, octaves, pixelation and seed. Edit terrain bands or add/remove terrains. Click "Generate Terrain" to create and view the image.

The generated image is saved as `output.png` in the project directory.
