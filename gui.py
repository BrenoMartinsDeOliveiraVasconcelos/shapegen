import sys
from sys import argv as args
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QFormLayout, QScrollArea, QLineEdit, QColorDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont
import lib
import imageio.v3 as iio
import imageio
import time
import numpy as np
from PIL.Image import Image, NEAREST

SEED_MIN = 0
SEED_MAX = 100000
OUTPUT_FN = "output.png"
MAX_TERRAIN_SIZE = 8192
MAX_FPS = 1000
MIN_FPS = 15


class TerrainWorker(QThread):
    """Worker thread for terrain generation to prevent UI freezing"""
    finished = pyqtSignal(QImage)
    progress = pyqtSignal(int, int, float, str)  # current, total
    
    def __init__(self, params, terrains):
        super().__init__()
        self.params = params
        self.terrains = terrains
        self.start_time = time.time()
        self.last_emit = time.time()
        self.video_filename = "output.mp4"
        self.frame_buffer = [] # type: list[Image]
        self.buffer_size = 4000
        self.total_time = 0
        self.target_resolutuion_width = 1080
        self.w = self.params['w']
        self.h = self.params['h']
        self.video_duration = 240
        self.frames = 0
        self.record = params['record']


    def _flush_buffer(self):
        print("Flushing buffer to disk...")
        
        frame_num = 0
        for frame in self.frame_buffer:
            
            frame_num += 1
            aspect_ratio = self.h / self.w

            self.progress_emit(frame_num, len(self.frame_buffer), "Writing frames to disk")

            times_bigger_h = self.target_resolutuion_width * aspect_ratio / self.h
            times_bigger_w = self.target_resolutuion_width / self.w

            if times_bigger_h >= 1 :
                times_bigger_h = round(times_bigger_h)
            
            if times_bigger_w >= 1:
                times_bigger_w = round(times_bigger_w)

            if times_bigger_h < 1:
                times_bigger_h = round(times_bigger_h, 1)

            if times_bigger_w < 1:
                times_bigger_w = round(times_bigger_w, 1)

            final_resolution_h = int(self.h * times_bigger_h)
            final_resolution_w = int(self.w * times_bigger_w)

            frame = frame.resize((final_resolution_w, final_resolution_h), resample=NEAREST)

            frame_np = np.asarray(frame)

            self.writer.append_data(frame_np)

        self.frame_buffer.clear()

    
    def start_record(self):
        fps = round(self.frames / self.video_duration)

        if fps < MIN_FPS:
            fps = MIN_FPS
        
        if fps > MAX_FPS:
            fps = MAX_FPS

        self.writer = imageio.get_writer(self.video_filename, fps=fps)
        self.frame_buffer = []


    def append_video(self, frame: Image, frame_num, frame_count):
        self.frame_buffer.append(frame)

        if len(self.frame_buffer) >= self.buffer_size:
            self._flush_buffer()


    def stop_record(self):
        if self.frame_buffer:
            self._flush_buffer()

        self.writer.close()        


    def progress_emit(self, current, total, text="Generating color map"):
        if time.time() - self.last_emit < 0.1:
            return
        self.last_emit = time.time()

        self.total_time = time.time() - self.start_time
        self.progress.emit(current, total, self.total_time, text)

        
    def run(self):
        w = self.w
        h = self.h

        scale = self.params['scale']
        octaves = self.params['octaves']
        #pixelation_levels = self.params['pixelation_levels']
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

        #nmap_pixel = lib.pixelate_map(nmap, pixelation_levels)

        # Save noise map w/o pixelation
        noise_img = lib.create_image(w, h, (0, 0, 0))
        frame = 0

        frame_count = (nmap.shape[0] * nmap.shape[1])*2
        self.frames = frame_count
        total_steps = frame_count
        step_add = 1
        step = 0
        temp_frame_name = "frame.png"

        for y in range(nmap.shape[0]):
            for x in range(nmap.shape[1]):
                value = int(nmap[y, x] * 255)
                noise_img = lib.draw_pixel(noise_img, x, y, (value, value, value))
                step += step_add
                self.progress_emit(step, total_steps)
        noise_img.save("noise.png")
        
        # Create image
        img = lib.create_image(w, h, (0, 0, 0))

        # Save colored version
        for y in range(nmap.shape[0]):
            for x in range(nmap.shape[1]):
                value = lib.noise_color(int(nmap[y, x] * 255), variation=variation, terrains=self.terrains)
                
                img = lib.draw_pixel(img, x, y, value)
                step += step_add
                self.progress_emit(step, total_steps)

        print("Writing data...")
        img.save(OUTPUT_FN)

        # Write video
        if self.record:
            self.total_time = 0
            step = 0

            # Adjusting buffer size for RAM-safe usage
            base_pixels = 512*512
            total_pixels = w * h
            self.buffer_size = round((base_pixels / total_pixels) * self.buffer_size)
            
            lib.averages_step = []
            self.start_record()
            files = [noise_img, img]
            temp_file = lib.create_image(w, h, (0, 0, 0))
            for file in files:
                for height in range(h):
                    for width in range(w):
                        frame += 1
                        temp_file = lib.draw_pixel(temp_file, width, height, file.getpixel((width, height)))
                        self.append_video(temp_file.copy(), frame, frame_count)
                        step += step_add
                        self.progress_emit(step, total_steps, "Generating video")
                        

            self.stop_record()

        # Save to file
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
                "name": "Abyss",
                "level": 60,
                "base": [15, 20, 30]  # Very dark, almost black blue
            },
            {
                "name": "Deep Sea",
                "level": 90,
                "base": [30, 45, 60]  # Desaturated dark slate
            },
            {
                "name": "Shallows",
                "level": 105,
                "base": [50, 70, 80]  # Muted teal-grey
            },
            {
                "name": "Silt & Clay",
                "level": 115,
                "base": [100, 95, 85]  # Pallid, greyish beige (no bright yellow)
            },
            {
                "name": "Dead Grass",
                "level": 135,
                "base": [85, 90, 70]  # Pale olive/drab
            },
            {
                "name": "Deep Woods",
                "level": 165,
                "base": [45, 60, 50]  # Dark, desaturated pine green
            },
            {
                "name": "Stone",
                "level": 195,
                "base": [60, 60, 65]  # Dark slate grey
            },
            {
                "name": "Peaks",
                "level": 225,
                "base": [100, 100, 110] # Cold, lighter grey
            },
            {
                "name": "Glacier",
                "level": 256,
                "base": [180, 190, 200] # Dirty/Muted white
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
        self.record = False
        
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
        self.w_spin.setRange(2, MAX_TERRAIN_SIZE)
        self.w_spin.setValue(1024)
        self.w_spin.setSingleStep(64)
        params_layout.addRow("Width:", self.w_spin)
        
        # Height
        self.h_spin = QSpinBox()
        self.h_spin.setRange(2, MAX_TERRAIN_SIZE)
        self.h_spin.setValue(1024)
        self.h_spin.setSingleStep(64)
        params_layout.addRow("Height:", self.h_spin)
        
        # Scale
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.2, 500.0)
        self.scale_spin.setValue(1.75)
        self.scale_spin.setSingleStep(0.05)
        params_layout.addRow("Scale:", self.scale_spin)
        
        # Octaves
        self.octaves_spin = QSpinBox()
        self.octaves_spin.setRange(1, 16)
        self.octaves_spin.setValue(8)
        params_layout.addRow("Octaves:", self.octaves_spin)
        
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
        generate_layout = QHBoxLayout()
        generate_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.generate_btn = QPushButton("Generate Terrain")
        self.generate_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.generate_btn.clicked.connect(self.generate_terrain)
        generate_layout.addWidget(self.generate_btn)

        # Record checkbox
        self.record_checkbox = QCheckBox("Record")
        self.record_checkbox.stateChanged.connect(self.toggle_record)
        generate_layout.addWidget(self.record_checkbox)

        left_layout.addLayout(generate_layout)
        
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
        self.image_label.setStyleSheet("border: 2px solid #cccccc; background-color: #000000;")
        self.image_label.setText("Terrain will be displayed here")
        self.image_label.setMinimumSize(768, 768)
        self.image_label.setMaximumSize(768, 768)
        right_layout.addWidget(self.image_label)
        
        main_layout.addWidget(right_panel, 1)

    
    def toggle_record(self, state):
        self.record = state != 0

        
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
            'variation': self.variation_spin.value(),
            'seed': self.seed_spin.value(),
            'record': self.record
        }
        
        # Get terrains
        terrains = self.get_current_terrains()
        
        # Create and start worker thread
        self.worker = TerrainWorker(params, terrains)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.start()

    def update_progress(self, current, total, time_elapsed, text):
        percent = lib.percent(current, total)

        progress_str = f"{text}... {percent:.4f}% - {lib.seconds_to_human(time_elapsed)}"
        progress_str += f"\n{current}/{total}"
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