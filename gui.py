import sys
from sys import argv as args
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QFormLayout, QScrollArea, QLineEdit, QColorDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont
import lib
import imageio.v3 as iio
import imageio
import time
import PIL

SEED_MIN = 0
SEED_MAX = 100000
OUTPUT_FN = "output.png"

class TerrainWorker(QThread):
    """Worker thread for terrain generation to prevent UI freezing"""
    finished = pyqtSignal(QImage)
    progress = pyqtSignal(int, int, float)  # current, total
    
    def __init__(self, params, terrains):
        super().__init__()
        self.params = params
        self.terrains = terrains
        self.start_time = time.time()
        self.last_emit = time.time()
        self.video_filename = "output.mp4"

    
    def start_record(self):
        self.writer = imageio.get_writer(self.video_filename, fps=60)


    def append_video(self, frame, frame_num, frame_count):
        print(f"Adding frame {frame_num}/{frame_count}")
        image = iio.imread(frame)
        self.writer.append_data(image)

    
    def stop_record(self):        
        self.writer.close()        


    def progress_emit(self, current, total):
        if time.time() - self.last_emit < 0.1:
            return
        self.last_emit = time.time()
        total_time = time.time() - self.start_time
        self.progress.emit(current, total, total_time)

        
    def run(self):
        w = self.params['w']
        h = self.params['h']
        scale = self.params['scale']
        octaves = self.params['octaves']
        pixelation_levels = self.params['pixelation_levels']
        variation = self.params['variation']
        seed = self.params['seed']
        
        # Generate noise map
        nmap = lib.generate_noise_map(
            w, h, 
            scale=scale, 
            octaves=octaves, 
            persistence=0.5, 
            seed=seed, 
            lacunarity=2.0
        )

        nmap_pixel = lib.pixelate_map(nmap, pixelation_levels)

        # Save noise map w/o pixelation
        noise_img = lib.create_image(w, h, (0, 0, 0))
        frame = 0

        frame_count = (nmap.shape[0] * nmap.shape[1])*3
        total_steps = frame_count
        step_add = 1
        if "record" in args:
            total_steps = total_steps * 3
        step = 0
        temp_frame_name = "frame.png"

        for y in range(nmap.shape[0]):
            for x in range(nmap.shape[1]):
                frame += 1
                value = int(nmap[y, x] * 255)
                noise_img = lib.draw_pixel(noise_img, x, y, (value, value, value))
                step += step_add
                self.progress_emit(step, total_steps)
        noise_img.save("noise.png")


        # Save noise map w/ pixelation
        pixel_img = lib.create_image(w, h, (0, 0, 0))
        for y in range(nmap_pixel.shape[0]):
            for x in range(nmap_pixel.shape[1]):
                frame += 1
                value = int(nmap_pixel[y, x] * 255)
                pixel_img = lib.draw_pixel(pixel_img, x, y, (value, value, value))
                step += step_add
                self.progress_emit(step, total_steps)

                    
        pixel_img.save("pixel.png")

        
        # Create image
        img = lib.create_image(w, h, (0, 0, 0))

        # Save colored version
        for y in range(nmap_pixel.shape[0]):
            for x in range(nmap_pixel.shape[1]):
                frame += 1
                value = lib.noise_color(int(nmap[y, x] * 255), variation=variation, terrains=self.terrains)
                
                img = lib.draw_pixel(img, x, y, value)
                step += step_add
                self.progress_emit(step, total_steps)

        # Write video
        if "record" in args:
            self.start_record()
            files = [noise_img, nmap_pixel, img]
            temp_file = lib.create_image(w, h, (0, 0, 0))
            for file in files:
                for height in range(h):
                    for width in range(w):
                        temp_file = lib.draw_pixel(temp_file, width, height, file.getpixel((width, height)))
                        self.append_video(temp_file, frame, frame_count)
                        step += step_add
                        self.progress_emit(step, total_steps)
                        

            self.stop_record()

        # Save to file
        print("Writing data...")
        img.save(OUTPUT_FN)
        print("Loading to GUI...")
        qimage = QImage(OUTPUT_FN)
        qimage_safe = qimage.copy()
        
        print("Finished!")
        self.finished.emit(qimage_safe)


class TerrainWidget(QWidget):
    """Widget for editing a single terrain type"""
    def __init__(self, terrain_data, index):
        super().__init__()
        self.index = index
        self.terrain_data = terrain_data
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel(f"Terrain {self.index+1}")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Form layout for properties
        form = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.terrain_data['name'])
        form.addRow("Name:", self.name_edit)
        
        # Level
        self.level_spin = QSpinBox()
        self.level_spin.setRange(0, 256)
        self.level_spin.setValue(self.terrain_data['level'])
        form.addRow("Top Level:", self.level_spin)
        
        # Variation
        self.variation_spin = QSpinBox()
        self.variation_spin.setRange(0, 255)
        if 'variation' in self.terrain_data:
            self.variation_spin.setValue(self.terrain_data['variation'])
        else:
            self.variation_spin.setValue(0)
            self.variation_spin.setSpecialValueText("Global")
        form.addRow("Variation:", self.variation_spin)
        
        # Color selection
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(50, 20)
        color_layout.addWidget(self.color_preview)
        
        self.r_spin = QSpinBox()
        self.r_spin.setRange(0, 255)
        self.r_spin.setValue(self.terrain_data['base'][0])
        self.r_spin.valueChanged.connect(self.update_color_preview)
        color_layout.addWidget(QLabel("R:"))
        color_layout.addWidget(self.r_spin)
        
        self.g_spin = QSpinBox()
        self.g_spin.setRange(0, 255)
        self.g_spin.setValue(self.terrain_data['base'][1])
        self.g_spin.valueChanged.connect(self.update_color_preview)
        color_layout.addWidget(QLabel("G:"))
        color_layout.addWidget(self.g_spin)
        
        self.b_spin = QSpinBox()
        self.b_spin.setRange(0, 255)
        self.b_spin.setValue(self.terrain_data['base'][2])
        self.b_spin.valueChanged.connect(self.update_color_preview)
        color_layout.addWidget(QLabel("B:"))
        color_layout.addWidget(self.b_spin)
        self.color_btn = QPushButton("Set")
        self.color_btn.clicked.connect(self.show_color_dialog)
        color_layout.addWidget(self.color_btn)
        
        form.addRow("Color:", color_layout)
        layout.addLayout(form)
        
        self.setLayout(layout)
        self.update_color_preview()
        
    def update_color_preview(self):
        r = self.r_spin.value()
        g = self.g_spin.value()
        b = self.b_spin.value()
        self.color_preview.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid black;")

    
    def show_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.r_spin.setValue(color.red())
            self.g_spin.setValue(color.green())
            self.b_spin.setValue(color.blue())


    def get_terrain_data(self):
        data = {
            'name': self.name_edit.text(),
            'level': self.level_spin.value(),
            'base': [self.r_spin.value(), self.g_spin.value(), self.b_spin.value()]
        }
        if self.variation_spin.value() > 0:
            data['variation'] = self.variation_spin.value()
        return data


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.terrains = [
            {
                "name": "Ocean",
                "level": 135,
                "base": [34, 63, 168]
            },
            {   
                "name": "Beach",
                "level": 160,
                "base": [168, 179, 8]
            },
            {
                "name": "Grassland",
                "level": 195,
                "base": [33, 98, 38]
            },
            {
                "name": "Mountains",
                "level": 210,
                "base": [50, 50, 50]
            },
            {
                "name": "Snow",
                "level": 256,
                "base": [255, 255, 255]
            }
        ]
        self.worker = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Terrain Generator")
        window_w = 1330
        window_h = 800
        self.resize(window_w, window_h)
        self.setMaximumHeight(window_h)
        self.setMaximumWidth(window_w)
        self.setMinimumHeight(window_h)
        self.setMinimumWidth(window_w)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Parameters group
        params_group = QGroupBox("Generation Parameters")
        params_layout = QFormLayout()
        
        # Width
        self.w_spin = QSpinBox()
        self.w_spin.setRange(2, 8192)
        self.w_spin.setValue(1024)
        self.w_spin.setSingleStep(1)
        params_layout.addRow("Width:", self.w_spin)
        
        # Height
        self.h_spin = QSpinBox()
        self.h_spin.setRange(2, 8192)
        self.h_spin.setValue(1024)
        self.h_spin.setSingleStep(1)
        params_layout.addRow("Height:", self.h_spin)
        
        # Scale
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 10.0)
        self.scale_spin.setValue(1.75)
        self.scale_spin.setSingleStep(0.01)
        params_layout.addRow("Scale:", self.scale_spin)
        
        # Octaves
        self.octaves_spin = QSpinBox()
        self.octaves_spin.setRange(1, 16)
        self.octaves_spin.setValue(8)
        params_layout.addRow("Octaves:", self.octaves_spin)
        
        # Pixelation Levels
        self.pixelation_spin = QSpinBox()
        self.pixelation_spin.setRange(2, 512)
        self.pixelation_spin.setValue(256)
        params_layout.addRow("Pixelation Level:", self.pixelation_spin)
        
        # Variation
        self.variation_spin = QSpinBox()
        self.variation_spin.setRange(0, 255)
        self.variation_spin.setValue(255)
        params_layout.addRow("Variation:", self.variation_spin)
        
        # Seed
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(SEED_MIN, SEED_MAX)
        self.seed_spin.setValue(random.randint(SEED_MIN, SEED_MAX))
        params_layout.addRow("Seed:", self.seed_spin)
        
        # Random seed button
        self.random_seed_btn = QPushButton("Random Seed")
        self.random_seed_btn.clicked.connect(self.randomize_seed)
        params_layout.addRow("", self.random_seed_btn)

        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        
        # Terrain configuration group
        terrain_group = QGroupBox("Terrain Configuration")
        terrain_layout = QVBoxLayout()
        
        # Scroll area for terrain widgets
        self.terrain_scroll = QScrollArea()
        self.terrain_scroll.setWidgetResizable(True)
        self.terrain_container = QWidget()
        self.terrain_layout = QVBoxLayout(self.terrain_container)
        
        # Add existing terrain widgets
        self.terrain_widgets = []
        for i, terrain in enumerate(self.terrains):
            widget = TerrainWidget(terrain, i)
            self.terrain_widgets.append(widget)
            self.terrain_layout.addWidget(widget)
        
        self.terrain_scroll.setWidget(self.terrain_container)
        terrain_layout.addWidget(self.terrain_scroll)
        
        # Add/Remove terrain buttons
        terrain_buttons_layout = QHBoxLayout()
        self.add_terrain_btn = QPushButton("Add Terrain")
        self.add_terrain_btn.clicked.connect(self.add_terrain)
        self.remove_terrain_btn = QPushButton("Remove Last Terrain")
        self.remove_terrain_btn.clicked.connect(self.remove_terrain)
        terrain_buttons_layout.addWidget(self.add_terrain_btn)
        terrain_buttons_layout.addWidget(self.remove_terrain_btn)
        terrain_layout.addLayout(terrain_buttons_layout)
        
        terrain_group.setLayout(terrain_layout)
        left_layout.addWidget(terrain_group)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Terrain")
        self.generate_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.generate_btn.clicked.connect(self.generate_terrain)
        left_layout.addWidget(self.generate_btn)
        
        # Progress label
        self.progress_label = QLabel("Ready")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.progress_label)
        
        # Image info
        self.image_info = QLabel("No image generated yet")
        self.image_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.image_info)

        # Add left panel to main layout
        main_layout.addWidget(left_panel)
        
        # Right panel for image display
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #cccccc; background-color: #f0f0f0;")
        self.image_label.setText("Terrain will be displayed here")
        self.image_label.setMinimumSize(768, 768)
        self.image_label.setMaximumSize(768, 768)
        right_layout.addWidget(self.image_label)
        
        main_layout.addWidget(right_panel, 1)
        
    def randomize_seed(self):
        self.seed_spin.setValue(random.randint(SEED_MIN, SEED_MAX))
        
    def add_terrain(self):
        new_terrain = {
            "name": "New Terrain",
            "level": 150,
            "base": [random.randint(0, 255) for _ in range(3)]
        }
        self.terrains.append(new_terrain)
        widget = TerrainWidget(new_terrain, len(self.terrains) - 1)
        self.terrain_widgets.append(widget)
        self.terrain_layout.addWidget(widget)
        
    def remove_terrain(self):
        if len(self.terrains) > 1:
            self.terrains.pop()
            widget = self.terrain_widgets.pop()
            widget.deleteLater()

            
    def get_current_terrains(self):
        terrains = []
        for widget in self.terrain_widgets:
            terrains.append(widget.get_terrain_data())
        # Sort by level for proper terrain ordering
        terrains.sort(key=lambda x: x['level'])
        return terrains
        
    def generate_terrain(self):
        # Disable generate button during generation
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating...")
        self.progress_label.setText("Generating noise map...")
        
        # Get parameters
        params = {
            'w': self.w_spin.value(),
            'h': self.h_spin.value(),
            'scale': self.scale_spin.value(),
            'octaves': self.octaves_spin.value(),
            'pixelation_levels': self.pixelation_spin.value(),
            'variation': self.variation_spin.value(),
            'seed': self.seed_spin.value()
        }
        
        # Get terrains
        terrains = self.get_current_terrains()
        
        # Create and start worker thread
        self.worker = TerrainWorker(params, terrains)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.start()
        
    def update_progress(self, current, total, time_elapsed):
        percent = lib.percent(current, total)
        estimated_time = lib.estimate_end_time(percent, time_elapsed)
        progress_str = f"Processing... {percent:.2f}% - {lib.seconds_to_human(time_elapsed)} (Estimated: {lib.seconds_to_human(estimated_time)})"
        progress_str += f"\n{current}/{total}"
        print(progress_str)
        self.progress_label.setText(progress_str)
        
    def on_generation_finished(self, qimage):
        # Display the image
        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
        # Update info
        w = self.w_spin.value()
        h = self.h_spin.value()
        self.image_info.setText(f"Size: {w}×{h} (displayed scaled)")
        
        # Re-enable buttons
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Terrain")
        self.progress_label.setText("Generation complete!")
        
        
    def resizeEvent(self, event):
        """Handle window resize to scale image appropriately"""
        super().resizeEvent(event)
        if hasattr(self.image_label, 'pixmap') and self.image_label.pixmap():
            pixmap = self.image_label.pixmap()
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()