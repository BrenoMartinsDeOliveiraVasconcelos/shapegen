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

# Run
* Open a terminal in the project directory (where `gui.py` and `lib.py` live).
* Run:

```bash
python gui.py
```

* Use the left panel to adjust width, height, scale, octaves, pixelation and seed. Edit terrain bands or add/remove terrains. Click "Generate Terrain" to create and view the image.

The generated image is saved as `output.png` in the project directory.
