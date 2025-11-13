import tkinter as tk
from tkinter import ttk
import pyautogui
import pydirectinput
import cv2
import numpy as np
import platform
import random
import threading
import time
from typing import Optional, Tuple
import os
import sys
from datetime import datetime

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MiningMacroNoSpiders:
    def __init__(self, root):
        """Initialize the mining macro application."""
        self.root = root
        self.root.title("Mining Macro (No Spiders)")
        
        # State
        self.detection_region_1: Optional[Tuple[int, int, int, int]] = None
        self.detection_region_2: Optional[Tuple[int, int, int, int]] = None
        self.spider_detection_region: Optional[Tuple[int, int, int, int]] = None
        self.fire_detection_region: Optional[Tuple[int, int, int, int]] = None
        self.click_point_1: Optional[Tuple[int, int]] = None
        self.click_point_2: Optional[Tuple[int, int]] = None
        self.spider_attack_point_1: Optional[Tuple[int, int]] = None
        self.spider_attack_point_2: Optional[Tuple[int, int]] = None
        self.character_point: Optional[Tuple[int, int]] = None
        self.character_marker_id: Optional[int] = None
        self.running: bool = False
        self.overlay = None
        self.asset_status_var = tk.StringVar(value="Checking assets...")
        self.confidence_var = tk.StringVar(value="Confidence: N/A")
        self.current_strategy: int = 1
        
        # Stopwatch and rock counter
        self.total_elapsed_time: float = 0.0
        self.session_start_time: Optional[float] = None
        self.rock_counter: int = 0
        self.stopwatch_var = tk.StringVar(value="Stopwatch: 00:00:00")
        self.rock_counter_var = tk.StringVar(value="Rocks Mined: 0")
        
        # Direction switching state
        self.last_direction = None
        self.direction_switches = 0
        self.direction_switches_var = tk.StringVar(value="Direction Switches: 0")
        
        self.mined_rock_templates = ['rock_phase_4.png']
        # Spider templates including the new leg assets for better detection
        self.spider_templates = [
            'spider1.png', 'spider2.png', 'spider3.png', 'spider4.png',
            'spider1_legs_1.png', 'spider1_legs_2.png',
            'spider4_legs_1.png', 'spider4_legs_2.png'
        ]  # Spider templates including leg variations
        
        # Relative offsets from character point
        self.relative_mining_offset_1: Optional[Tuple[int, int]] = None
        self.relative_mining_offset_2: Optional[Tuple[int, int]] = None
        self.relative_spider_attack_offset_1: Optional[Tuple[int, int]] = None
        self.relative_spider_attack_offset_2: Optional[Tuple[int, int]] = None
        
        # Detection confidence
        self.detection_confidence_var = tk.StringVar(value="0.5")
        self.detection_confidence: float = 0.5
        
        # Spider detection confidence
        self.spider_confidence_var = tk.StringVar(value="0.7")
        self.spider_confidence: float = 0.7
        
        # Spider attack status
        self.spider_status_var = tk.StringVar(value="Spider: Not Detected")
        self.spider_attack_in_progress = False
        
        # Debug settings
        self.ENABLE_DEBUG = False
        self.debug_screenshot_count = 0
        self.max_debug_screenshots = 5
        self.debug_screenshot_dir = "debug_screenshots"
        if self.ENABLE_DEBUG:
            self.setup_debug_dir()
            
        # Timeout settings (in seconds)
        self.area_switch_timeout = 5.0  # Time to wait when switching areas
        self.mining_retry_timeout = 2.0  # Time to wait between mining attempts
        
        self.create_ui()
        self._check_assets_loaded()
        
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
    
    def setup_debug_dir(self):
        """Create debug directory if it doesn't exist."""
        os.makedirs(self.debug_screenshot_dir, exist_ok=True)
        
    def save_debug_screenshot(self, screenshot, prefix="debug", confidence=0.0):
        """Save a screenshot with debug information."""
        if not self.ENABLE_DEBUG or self.debug_screenshot_count >= self.max_debug_screenshots:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(
                self.debug_screenshot_dir,
                f"{prefix}_{timestamp}_conf_{confidence:.2f}.png"
            )
            cv2.imwrite(filename, screenshot)
            self.debug_screenshot_count += 1
            print(f"[DEBUG] Saved debug screenshot: {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to save debug screenshot: {e}")
    
    def _check_assets_loaded(self):
        """Verify that all required asset images can be loaded."""
        required_assets = [
            'rock_phase_1.png', 'rock_phase_2.png', 'rock_phase_3.png', 
            'rock_phase_4.png'
        ]
        
        all_loaded = True
        failed_assets = []
        
        for asset_file in required_assets:
            try:
                asset_path = resource_path(f'assets/{asset_file}')
                img = cv2.imread(asset_path)
                if img is None:
                    all_loaded = False
                    failed_assets.append(asset_file)
                    print(f"ERROR: Could not load asset: {asset_path}")
            except Exception as e:
                all_loaded = False
                failed_assets.append(asset_file)
                print(f"ERROR: Exception loading asset {asset_path}: {e}")
        
        if all_loaded:
            self.asset_status_var.set("Assets Loaded: OK")
            self.asset_status_label.config(foreground='green')
        else:
            self.asset_status_var.set(f"Assets Loaded: ERROR ({', '.join(failed_assets)})")
            self.asset_status_label.config(foreground='red')
            self.start_btn.config(state=tk.DISABLED)
            self.reset_btn.config(state=tk.DISABLED)
        
        return all_loaded
    
    def create_ui(self):
        """Create the main UI components."""
        self.frame = ttk.Frame(self.root, padding="5")
        self.frame.pack(padx=5, pady=5)
        
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_macro, width=8, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_macro, state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.reset_btn = ttk.Button(btn_frame, text="Reset Selection", command=self.setup_region, width=15, state=tk.DISABLED)
        self.reset_btn.pack(side=tk.LEFT, padx=2)
        
        # Confidence controls frame
        confidence_frame = ttk.Frame(self.frame)
        confidence_frame.pack(fill='x', pady=5)
        
        # Detection confidence
        detection_frame = ttk.Frame(confidence_frame)
        detection_frame.pack(fill='x', pady=2)
        ttk.Label(detection_frame, text="Rock Detection:").pack(side='left')
        confidence_entry = ttk.Entry(detection_frame, textvariable=self.detection_confidence_var, width=5)
        confidence_entry.pack(side='left', padx=5)
        confidence_entry.bind('<Return>', self._validate_detection_confidence)
        confidence_entry.bind('<FocusOut>', self._validate_detection_confidence)
        
        # Spider confidence
        spider_frame = ttk.Frame(confidence_frame)
        spider_frame.pack(fill='x', pady=2)
        ttk.Label(spider_frame, text="Spider Detection:").pack(side='left')
        spider_confidence_entry = ttk.Entry(spider_frame, textvariable=self.spider_confidence_var, width=5)
        spider_confidence_entry.pack(side='left', padx=5)
        spider_confidence_entry.bind('<Return>', self._validate_spider_confidence)
        spider_confidence_entry.bind('<FocusOut>', self._validate_spider_confidence)
        
        # Timeout settings frame
        timeout_frame = ttk.Frame(self.frame)
        timeout_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Area switch timeout
        ttk.Label(timeout_frame, text="Area Switch (s):").pack(side=tk.LEFT, padx=(0, 5))
        self.area_switch_var = tk.StringVar(value="5.0")
        self.area_switch_entry = ttk.Entry(timeout_frame, textvariable=self.area_switch_var, width=5)
        self.area_switch_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.area_switch_entry.bind("<FocusOut>", self._validate_timeout_values)
        self.area_switch_entry.bind("<Return>", self._validate_timeout_values)
        
        # Mining retry timeout
        ttk.Label(timeout_frame, text="Mining Retry (s):").pack(side=tk.LEFT, padx=(0, 5))
        self.mining_retry_var = tk.StringVar(value="2.0")
        self.mining_retry_entry = ttk.Entry(timeout_frame, textvariable=self.mining_retry_var, width=5)
        self.mining_retry_entry.pack(side=tk.LEFT)
        self.mining_retry_entry.bind("<FocusOut>", self._validate_timeout_values)
        self.mining_retry_entry.bind("<Return>", self._validate_timeout_values)
        
        # Indicators frame
        indicators_frame = ttk.Frame(self.frame)
        indicators_frame.pack(fill=tk.X, pady=(5, 2))
        
        stopwatch_label = ttk.Label(indicators_frame, textvariable=self.stopwatch_var, font=('TkDefaultFont', 9), foreground='black')
        stopwatch_label.pack(side=tk.LEFT, padx=(0, 10))
        
        rock_counter_label = ttk.Label(indicators_frame, textvariable=self.rock_counter_var, font=('TkDefaultFont', 9), foreground='black')
        rock_counter_label.pack(side=tk.LEFT)
        
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self.frame, textvariable=self.status_var, font=('TkDefaultFont', 10, 'bold'), foreground='blue')
        status.pack(pady=(5, 0))
        
        # Spider status display
        spider_status = ttk.Label(self.frame, textvariable=self.spider_status_var, 
                               font=('TkDefaultFont', 10), foreground='red')
        spider_status.pack(pady=(2, 5))

        self.asset_status_label = ttk.Label(self.frame, textvariable=self.asset_status_var, font=('TkDefaultFont', 9), foreground='gray')
        self.asset_status_label.pack(pady=(0, 5))

        confidence_label = ttk.Label(self.frame, textvariable=self.confidence_var, font=('TkDefaultFont', 9), foreground='purple')
        confidence_label.pack(pady=(0, 2))
        
        # Add direction switches counter display
        direction_label = ttk.Label(self.frame, textvariable=self.direction_switches_var, font=('TkDefaultFont', 9), foreground='orange')
        direction_label.pack(pady=(0, 5))
        
        self.setup_region()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        
    def _validate_detection_confidence(self, event=None):
        """Validate and update the detection confidence."""
        try:
            confidence = float(self.detection_confidence_var.get())
            if 0.1 <= confidence <= 1.0:
                self.detection_confidence = confidence
                self.status_var.set(f"Rock detection confidence set to {confidence}")
            else:
                self.status_var.set("Confidence must be between 0.1 and 1.0")
                self.detection_confidence_var.set("0.5")
                self.detection_confidence = 0.5
        except ValueError:
            self.status_var.set("Invalid confidence value")
            self.detection_confidence_var.set("0.5")
            self.detection_confidence = 0.5
            
    def _validate_spider_confidence(self, event=None):
        """Validate and update the spider detection confidence."""
        try:
            confidence = float(self.spider_confidence_var.get())
            if 0.1 <= confidence <= 1.0:
                self.spider_confidence = confidence
                self.status_var.set(f"Spider detection confidence set to {confidence}")
            else:
                self.status_var.set("Spider confidence must be between 0.1 and 1.0")
                self.spider_confidence_var.set("0.7")
                self.spider_confidence = 0.7
        except ValueError:
            self.status_var.set("Invalid spider confidence value")
            self.spider_confidence_var.set("0.7")
            self.spider_confidence = 0.7
    
    def _validate_timeout_values(self, event=None):
        """Validate and update the timeout values."""
        try:
            # Validate area switch timeout
            area_switch = float(self.area_switch_var.get())
            if area_switch < 0.1:
                raise ValueError("Area switch timeout must be at least 0.1 seconds.")
            self.area_switch_timeout = area_switch
            
            # Validate mining retry timeout
            mining_retry = float(self.mining_retry_var.get())
            if mining_retry < 0.1:
                raise ValueError("Mining retry timeout must be at least 0.1 seconds.")
            self.mining_retry_timeout = mining_retry
            
            self.status_var.set(f"Timeouts updated: Switch={self.area_switch_timeout:.1f}s, Retry={self.mining_retry_timeout:.1f}s")
        except ValueError as e:
            # Reset to last valid values
            self.area_switch_var.set(f"{self.area_switch_timeout:.1f}")
            self.mining_retry_var.set(f"{self.mining_retry_timeout:.1f}")
            self.status_var.set(f"Invalid timeout: {str(e)}")

    def update_stopwatch(self):
        """Update the stopwatch label every second."""
        if self.running and self.session_start_time is not None:
            current_elapsed_in_session = time.time() - self.session_start_time
            display_time = self.total_elapsed_time + current_elapsed_in_session
            
            hours, remainder = divmod(int(display_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.stopwatch_var.set(f"Stopwatch: {hours:02}:{minutes:02}:{seconds:02}")
            self.root.after(1000, self.update_stopwatch)

    def setup_region(self):
        """Open an overlay to select screen regions."""
        self.reset_selection()

        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.3)
        
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0, cursor='cross', bg='black', bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.selection_phase = 0 # 0: click_1, 1: region_1, 2: click_2, 3: region_2, 4: spider_region, 5: spider_attack, 6: character, 7: fire_region
        
        self.detection_region_1_start = None
        self.detection_region_1_rect_id = None
        self.detection_region_2_start = None
        self.detection_region_2_rect_id = None
        
        self.click_point_1 = None
        self.click_point_2 = None
        self.click_marker_ids = []
        self.character_point = None
        self.character_marker_id = None
        
        screen_width = self.overlay.winfo_screenwidth()
        self.instruction_text = self.canvas.create_text(
            screen_width // 2, 30, text="", fill="white", font=('Arial', 12, 'bold'),
            anchor='center', justify='center', tags='instruction'
        )
        self.update_instructions()
        
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<Button-3>', self.on_right_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.overlay.bind('<Escape>', self.cancel_selection)
        self.overlay.bind('<Return>', self.confirm_region)
        
        self.overlay.grab_set()
        
    def on_click(self, event):
        """Handle mouse clicks for point selection."""
        if self.selection_phase == 0: # Click point 1
            self.set_click_point(event.x, event.y, 'mining_1')
        elif self.selection_phase == 1: # Detection region 1
            if self.detection_region_1_rect_id is None: self.detection_region_1_start = (event.x, event.y)
        elif self.selection_phase == 2: # Click point 2
            self.set_click_point(event.x, event.y, 'mining_2')
        elif self.selection_phase == 3: # Detection region 2
            if self.detection_region_2_rect_id is None: self.detection_region_2_start = (event.x, event.y)
        elif self.selection_phase == 4: # Spider detection region
            if not hasattr(self, 'spider_detection_region_start'):
                self.spider_detection_region_start = (event.x, event.y)
            else:
                # Create rectangle from start to current point
                x1, y1 = self.spider_detection_region_start
                x2, y2 = event.x, event.y
                if abs(x2 - x1) < 20 or abs(y2 - y1) < 20:
                    self.status_var.set("Selection too small.")
                    return
                self.spider_detection_region = (
                    min(x1, x2), min(y1, y2),
                    abs(x2 - x1), abs(y2 - y1)
                )
                self.selection_phase = 5
                self.update_instructions()
        elif self.selection_phase == 5: # Spider attack points
            if not hasattr(self, 'spider_attack_point_1') or self.spider_attack_point_1 is None:
                self.spider_attack_point_1 = (event.x, event.y)
                self.draw_click_marker(event.x, event.y, 'magenta', 'spider_attack_1')
                self.status_var.set("First spider attack point set. Click for second point.")
            elif not hasattr(self, 'spider_attack_point_2') or self.spider_attack_point_2 is None:
                self.spider_attack_point_2 = (event.x, event.y)
                self.draw_click_marker(event.x, event.y, 'magenta', 'spider_attack_2')
                self.status_var.set("Second spider attack point set. Right-click to set character position.")
                self.selection_phase = 6
                self.update_instructions()
        elif self.selection_phase == 7: # Fire detection region
            if not hasattr(self, 'fire_detection_region_start'):
                self.fire_detection_region_start = (event.x, event.y)
            else:
                # Create rectangle from start to current point
                x1, y1 = self.fire_detection_region_start
                x2, y2 = event.x, event.y
                if abs(x2 - x1) < 20 or abs(y2 - y1) < 20:
                    self.status_var.set("Selection too small.")
                    return
                self.fire_detection_region = (
                    min(x1, x2), min(y1, y2),
                    abs(x2 - x1), abs(y2 - y1)
                )
                self.selection_phase = 8
                self.update_instructions()
    
    def on_drag(self, event):
        """Handle mouse drag for region selection."""
        if self.selection_phase == 1: # Detection region 1
            if not self.detection_region_1_start: return
            x1, y1 = self.detection_region_1_start
            x2, y2 = event.x, event.y
            if self.detection_region_1_rect_id: self.canvas.coords(self.detection_region_1_rect_id, x1, y1, x2, y2)
            else: self.detection_region_1_rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline='cyan', fill='blue', stipple='gray50', width=2, tags='selection')
        elif self.selection_phase == 3: # Detection region 2
            if not self.detection_region_2_start: return
            x1, y1 = self.detection_region_2_start
            x2, y2 = event.x, event.y
            if self.detection_region_2_rect_id: self.canvas.coords(self.detection_region_2_rect_id, x1, y1, x2, y2)
            else: self.detection_region_2_rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline='lime', fill='green', stipple='gray50', width=2, tags='selection')
        elif self.selection_phase == 4: # Spider detection region
            if not hasattr(self, 'spider_detection_region_start'): return
            x1, y1 = self.spider_detection_region_start
            x2, y2 = event.x, event.y
            if hasattr(self, 'spider_detection_rect_id'):
                self.canvas.coords(self.spider_detection_rect_id, x1, y1, x2, y2)
            else:
                self.spider_detection_rect_id = self.canvas.create_rectangle(
                    x1, y1, x2, y2, 
                    outline='magenta', 
                    fill='purple', 
                    stipple='gray50', 
                    width=2, 
                    tags='selection'
                )
        elif self.selection_phase == 7: # Fire detection region
            if not hasattr(self, 'fire_detection_region_start'): return
            x1, y1 = self.fire_detection_region_start
            x2, y2 = event.x, event.y
            if hasattr(self, 'fire_detection_rect_id'):
                self.canvas.coords(self.fire_detection_rect_id, x1, y1, x2, y2)
            else:
                self.fire_detection_rect_id = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline='red',
                    fill='dark red',
                    stipple='gray50',
                    width=2,
                    tags='selection'
                )

    def on_release(self, event):
        """Finalize region selection on mouse release."""
        if self.selection_phase == 1: # Detection region 1
            if not (self.detection_region_1_start and self.detection_region_1_rect_id): return
            x1, y1, x2, y2 = self.canvas.coords(self.detection_region_1_rect_id)
            if abs(x2 - x1) < 20 or abs(y2 - y1) < 20: self.status_var.set("Selection too small."); return
            self.detection_region_1 = (int(min(x1, x2)), int(min(y1, y2)), int(abs(x2 - x1)), int(abs(y2 - y1)))
            self.selection_phase = 2
            self.update_instructions()
        elif self.selection_phase == 3: # Detection region 2
            if not (self.detection_region_2_start and self.detection_region_2_rect_id): return
            x1, y1, x2, y2 = self.canvas.coords(self.detection_region_2_rect_id)
            if abs(x2 - x1) < 20 or abs(y2 - y1) < 20: self.status_var.set("Selection too small."); return
            self.detection_region_2 = (int(min(x1, x2)), int(min(y1, y2)), int(abs(x2 - x1)), int(abs(y2 - y1)))
            self.selection_phase = 4
            self.update_instructions()
        elif self.selection_phase == 4: # Spider detection region
            if not hasattr(self, 'spider_detection_region_start'): return
            x1, y1 = self.spider_detection_region_start
            x2, y2 = event.x, event.y
            if abs(x2 - x1) < 20 or abs(y2 - y1) < 20: 
                self.status_var.set("Selection too small.")
                return
            self.spider_detection_region = (
                int(min(x1, x2)), 
                int(min(y1, y2)), 
                int(abs(x2 - x1)), 
                int(abs(y2 - y1))
            )
            self.selection_phase = 5
            self.update_instructions()
        elif self.selection_phase == 7: # Fire detection region
            if not hasattr(self, 'fire_detection_region_start') or not hasattr(self, 'fire_detection_rect_id'):
                return
                
            x1, y1 = self.fire_detection_region_start
            x2, y2 = event.x, event.y
            
            if abs(x2 - x1) < 20 or abs(y2 - y1) < 20:
                self.status_var.set("Selection too small.")
                return
                
            self.fire_detection_region = (
                int(min(x1, x2)),
                int(min(y1, y2)),
                int(abs(x2 - x1)),
                int(abs(y2 - y1))
            )
            self.selection_phase = 8
            self.update_instructions()

    def set_click_point(self, x, y, point_type):
        """Set the click point and update the marker."""
        if point_type == 'mining_1':
            self.click_point_1 = (x, y)
            self.draw_click_marker(x, y, 'cyan', 'mining_1')
            self.selection_phase = 1
        elif point_type == 'mining_2':
            self.click_point_2 = (x, y)
            self.draw_click_marker(x, y, 'lime', 'mining_2')
            self.selection_phase = 3
        self.update_instructions()

    def draw_click_marker(self, x, y, color, tag):
        """Draws a marker for a click point."""
        for marker_id in [id for id in self.click_marker_ids if tag in self.canvas.gettags(id)]:
            self.canvas.delete(marker_id)
        
        size = 10
        marker_ids = [
            self.canvas.create_line(x-size, y, x+size, y, fill=color, width=1, tags=(tag, 'click_point')),
            self.canvas.create_line(x, y-size, x, y+size, fill=color, width=1, tags=(tag, 'click_point')),
            self.canvas.create_oval(x-5, y-5, x+5, y+5, outline=color, width=1, tags=(tag, 'click_point'))
        ]
        self.click_marker_ids.extend(marker_ids)

    def on_right_click(self, event):
        """Handle right-click for character position selection."""
        if self.selection_phase == 6:  # Phase for setting character position
            self.set_character_point(event.x, event.y)
            self.status_var.set("Character position set. Press Enter to confirm.")

    def set_character_point(self, x, y):
        """Set the character's position."""
        self.character_point = (x, y)
        if self.character_marker_id: self.canvas.delete(self.character_marker_id)
        size = 7
        self.character_marker_id = self.canvas.create_rectangle(
            x - size, y - size, x + size, y + size,
            outline='red', fill='red', stipple='gray25', width=2, tags='character_point'
        )
        if hasattr(self, 'spider_attack_point_1') and hasattr(self, 'spider_attack_point_2'):
            self.selection_phase = 7
        else:
            self.selection_phase = 6
        self.update_instructions()
    
    def update_instructions(self):
        """Updates the instruction text on the overlay."""
        instructions = {
            0: "Phase 1/8: Set Mining Click Point 1.\n\nLeft-click your first mining action location.",
            1: "Phase 2/8: Select Detection Area 1.\n\nDrag a rectangle over the first rock's appearance area.",
            2: "Phase 3/8: Set Mining Click Point 2.\n\nLeft-click your second mining action location.",
            3: "Phase 4/8: Select Detection Area 2.\n\nDrag a rectangle over the second rock's appearance area.",
            4: "Phase 5/8: Set Spider Detection Area.\n\nDrag a rectangle where spiders can appear.",
            5: "Phase 6/8: Set Spider Attack Points.\n\nLeft-click two different positions to attack spiders from.",
            6: "Phase 7/8: Set Character Position.\n\nRight-click on your character's approximate center.",
            7: "Phase 8/8: Set Fire Detection Area.\n\nDrag a rectangle where fire should be detected.",
            8: "All selections complete!\n\nPress Enter to confirm or Esc to cancel."
        }
        
        # Only update if canvas and instruction_text exist
        if hasattr(self, 'canvas') and hasattr(self, 'instruction_text'):
            try:
                self.canvas.itemconfig(self.instruction_text, 
                                    text=instructions.get(self.selection_phase, "Unknown phase."))
            except (tk.TclError, AttributeError):
                # Canvas or text item might be destroyed
                pass
    
    def confirm_region(self, event=None):
        """Finalize the region and click point selection."""
        # Define required fields and their descriptions
        required_fields = {
            'click_point_1': (self.click_point_1, "Mining Click Point 1"),
            'detection_region_1': (self.detection_region_1, "Detection Area 1"),
            'click_point_2': (self.click_point_2, "Mining Click Point 2"),
            'detection_region_2': (self.detection_region_2, "Detection Area 2"),
            'spider_detection_region': (self.spider_detection_region, "Spider Detection Area"),
            'spider_attack_point_1': (self.spider_attack_point_1, "Spider Attack Point 1"),
            'spider_attack_point_2': (self.spider_attack_point_2, "Spider Attack Point 2"),
            'character_point': (self.character_point, "Character Position"),
            'fire_detection_region': (self.fire_detection_region, "Fire Detection Area")
        }
        
        # Check for missing fields
        missing_fields = [desc for field, (value, desc) in required_fields.items() if not value]
        
        if missing_fields:
            error_msg = "Missing required selections:\n"
            error_msg += "\n".join(f"- {field}" for field in missing_fields)
            self.status_var.set(error_msg)
            
            # Move to the first missing phase
            if not self.click_point_1:
                self.selection_phase = 0
            elif not self.detection_region_1:
                self.selection_phase = 1
            elif not self.click_point_2:
                self.selection_phase = 2
            elif not self.detection_region_2:
                self.selection_phase = 3
            elif not self.spider_detection_region:
                self.selection_phase = 4
            elif not self.spider_attack_point_1 or not self.spider_attack_point_2:
                self.selection_phase = 5
            elif not self.character_point:
                self.selection_phase = 6
                
            self.update_instructions()
            return
            
        # If we get here, all required fields are set
        try:
            # Calculate mining offsets
            self.relative_mining_offset_1 = (
                self.click_point_1[0] - self.character_point[0],
                self.click_point_1[1] - self.character_point[1]
            )
            self.relative_mining_offset_2 = (
                self.click_point_2[0] - self.character_point[0],
                self.click_point_2[1] - self.character_point[1]
            )
            # Calculate spider attack point offsets
            self.relative_spider_attack_offset_1 = (
                self.spider_attack_point_1[0] - self.character_point[0],
                self.spider_attack_point_1[1] - self.character_point[1]
            )
            self.relative_spider_attack_offset_2 = (
                self.spider_attack_point_2[0] - self.character_point[0],
                self.spider_attack_point_2[1] - self.character_point[1]
            )
        except Exception as e:
            self.status_var.set(f"Error during setup: {str(e)}")
            print(f"Error in confirm_region: {e}")
            return
            
        # Clean up the overlay
        self.cleanup_overlay()
        
        # Update the status and enable buttons
        self.status_var.set("Setup complete! Click 'Start Macro' to begin.")
        self.start_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
        
        # Reset the selection phase for next time
        self.selection_phase = 0
    
    def cleanup_overlay_elements(self):
        """Clear visual elements from the overlay."""
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            for tag in ['selection', 'click_point', 'character_point', 'instruction', 'spider_attack']:
                self.canvas.delete(tag)

    def reset_selection(self):
        """Reset the current selection and state."""
        # First clean up any existing overlay elements if canvas exists
        if hasattr(self, 'canvas') and self.canvas and self.canvas.winfo_exists():
            self.cleanup_overlay_elements()
        
        # Reset all points and regions
        self.selection_phase = 0
        self.detection_region_1 = None
        self.detection_region_2 = None
        self.spider_detection_region = None
        self.fire_detection_region = None
        self.click_point_1 = None
        self.click_point_2 = None
        self.spider_attack_point_1 = None
        self.spider_attack_point_2 = None
        self.character_point = None
        self.character_marker_id = None
        
        # Reset relative offsets
        self.relative_mining_offset_1 = None
        self.relative_mining_offset_2 = None
        self.relative_spider_attack_offset_1 = None
        self.relative_spider_attack_offset_2 = None
        
        # Recreate instruction text if canvas exists
        if hasattr(self, 'canvas') and self.canvas and self.canvas.winfo_exists():
            try:
                self.canvas.delete('all')
                self.instruction_text = self.canvas.create_text(
                    10, 10, anchor='nw', 
                    text="Phase 1/7: Set Mining Click Point 1.\n\nLeft-click your first mining action location.",
                    fill='white', font=('Arial', 12), width=300, tags='instruction'
                )
            except (tk.TclError, AttributeError):
                # Canvas might be destroyed during cleanup
                pass
        
        self.update_instructions()
        
        self.status_var.set("Ready")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        
        if hasattr(self, 'overlay') and self.overlay:
            self.update_instructions()

    def cancel_selection(self, event=None):
        """Cancel the selection process."""
        self.cleanup_overlay()
        self.reset_selection()

    def cleanup_overlay(self):
        """Clean up the overlay window and related attributes."""
        # First clean up any canvas elements
        if hasattr(self, 'canvas') and self.canvas and self.canvas.winfo_exists():
            try:
                self.cleanup_overlay_elements()
                self.canvas.destroy()
            except (tk.TclError, AttributeError):
                pass
        
        # Then destroy the overlay window
        if hasattr(self, 'overlay') and self.overlay:
            try:
                self.overlay.destroy()
            except tk.TclError:
                pass
            self.overlay = None
            
        # Clean up any remaining references
        if hasattr(self, 'canvas'):
            del self.canvas
        if hasattr(self, 'instruction_text'):
            del self.instruction_text

    def start_macro(self):
        """Start the mining macro."""
        if not all([self.detection_region_1, self.detection_region_2, self.click_point_1, self.click_point_2, self.character_point]):
            self.status_var.set("Error: All 5 setup phases not complete.")
            return
            
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.DISABLED)
        self.status_var.set("Running...")
        
        # Initialize counters and stopwatch
        self.session_start_time = time.time()
        self.rock_counter = 0
        self.rock_counter_var.set("Rocks Mined: 0")
        self.update_stopwatch()
        
        # Initialize direction tracking
        self.last_direction = self.current_strategy  # Set to current strategy at start
        self.direction_switches = 0
        self.direction_switches_var.set("Direction Switches: 0")
        
        self.macro_thread = threading.Thread(target=self.run_macro, daemon=True)
        self.macro_thread.start()
    
    def stop_macro(self):
        """Stop the mining macro."""
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.NORMAL)
        self.status_var.set("Stopped")
        
        # Accumulate elapsed time
        if self.session_start_time is not None:
            self.total_elapsed_time += (time.time() - self.session_start_time)
            self.session_start_time = None
        
        # Reset direction tracking when stopping
        self.last_direction = None
        self.direction_switches = 0
        self.direction_switches_var.set("Direction Switches: 0")

    def detect_fire(self):
        """Check the fire detection region for fire.png with confidence 0.5.
        
        Returns:
            tuple: (x, y) coordinates of the center of the detected fire, or None if not found
        """
        if not hasattr(self, 'fire_detection_region') or not self.fire_detection_region:
            print("[WARNING] No fire detection region set")
            return None
            
        try:
            # Take screenshot of the fire detection region
            x, y, w, h = self.fire_detection_region
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Check for fire with confidence 0.5
            fire_conf, fire_loc, fire_size = self.detect_any_template(
                screenshot_cv,
                ['fire.png'],
                confidence=0.8
            )
            
            if fire_conf > 0:
                # Convert local coordinates to screen coordinates
                fire_x = x + fire_loc[0] + (fire_size[0] // 2) if fire_size else x + fire_loc[0]
                fire_y = y + fire_loc[1] + (fire_size[1] // 2) if fire_size else y + fire_loc[1]
                return (fire_x, fire_y)
                
            return None
            
        except Exception as e:
            print(f"[ERROR] Error detecting fire: {e}")
            return None
            
    def detect_any_template(self, screenshot, templates, confidence=0.7):
        """Detect if any template matches in the screenshot."""
        best_match_val = 0.0
        best_match_loc = None
        best_match_template_size = None
        best_template_name = None
        
        for template_file in templates:
            try:
                template_path = resource_path(f'assets/{template_file}')
                template = cv2.imread(template_path)
                if template is None: continue
                if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]: continue
                
                result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if self.ENABLE_DEBUG and max_val < confidence and self.debug_screenshot_count < self.max_debug_screenshots:
                    debug_img = screenshot.copy()
                    h, w = template.shape[:2]
                    cv2.rectangle(debug_img, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 0, 255), 2)
                    self.save_debug_screenshot(debug_img, f"template_{template_file.replace('.png', '')}", max_val)
                
                if max_val > best_match_val:
                    best_match_val = max_val
                    best_match_loc = max_loc
                    best_match_template_size = (template.shape[1], template.shape[0])
                    best_template_name = template_file
            
            except Exception as e:
                print(f"[ERROR] Error processing template {template_file}: {e}")
        
        if self.ENABLE_DEBUG:
            if best_match_val > 0: print(f"[DEBUG] Best match: {best_template_name} with confidence: {best_match_val:.2f}")
            else:
                print("[DEBUG] No template matched.")
                if self.debug_screenshot_count < self.max_debug_screenshots: self.save_debug_screenshot(screenshot, "no_match", 0.0)
        
        return (best_match_val, best_match_loc, best_match_template_size) if best_match_val > confidence else (0.0, None, None)

    def check_for_spiders(self):
        """Check the spider detection region for spiders.
        
        Returns:
            tuple: (x, y) coordinates of the detected spider center, or None if no spider found
        """
        if not hasattr(self, 'spider_detection_enabled') or not self.spider_detection_enabled:
            return None
            
        if not self.spider_detection_region:
            if self.ENABLE_DEBUG:
                print("[DEBUG] No spider detection region set")
            return None
            
        # Take a screenshot of the spider detection region
        try:
            # Add some padding to the region to avoid edge effects
            padding = 20
            x, y, w, h = self.spider_detection_region
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(pyautogui.size().width - x, w + 2 * padding)
            h = min(pyautogui.size().height - y, h + 2 * padding)
            
            if w <= 0 or h <= 0:
                print(f"[WARN] Invalid spider detection region after padding: {self.spider_detection_region}")
                return None
                
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            if screenshot_cv is None or screenshot_cv.size == 0:
                print("[WARN] Failed to capture screenshot for spider detection")
                return None
            
            # Look for spiders in the detection region
            spider_conf, spider_loc, spider_size = self.detect_any_template(
                screenshot_cv, 
                self.spider_templates, 
                confidence=self.spider_confidence
            )
            
            if self.ENABLE_DEBUG:
                print(f"[DEBUG] Spider detection - Confidence: {spider_conf:.2f}, Location: {spider_loc}, Size: {spider_size}")
            
            if spider_conf > 0 and spider_loc is not None and spider_size is not None:
                # Convert local coordinates to screen coordinates
                spider_x = x + spider_loc[0] + (spider_size[0] // 2)
                spider_y = y + spider_loc[1] + (spider_size[1] // 2)
                
                if self.ENABLE_DEBUG:
                    print(f"[DEBUG] Spider detected at screen coordinates: ({spider_x}, {spider_y})")
                    
                self.spider_status_var.set(f"Spider Detected! (Confidence: {spider_conf:.2f})")
                return (spider_x, spider_y)
                
        except Exception as e:
            error_msg = f"Error checking for spiders: {str(e)}"
            print(f"[ERROR] {error_msg}")
            # If we get an error, disable spider detection for this session
            self.spider_detection_enabled = False
            self.status_var.set("Spider detection disabled due to error")
            
        return None

    def get_best_attack_point(self, spider_pos):
        """Determine the best attack point based on spider position.
        
        Args:
            spider_pos: (x, y) coordinates of the spider
            
        Returns:
            tuple: (x, y) coordinates of the best attack point, or None if not available
        """
        if not all([self.character_point, self.spider_attack_point_1, self.spider_attack_point_2]):
            return None
            
        # Calculate vectors from character to spider and attack points
        char_x, char_y = self.character_point
        spider_x, spider_y = spider_pos
        
        # Calculate vector from character to spider
        dx = spider_x - char_x
        dy = spider_y - char_y
        
        # Calculate distances to each attack point
        def distance_sq(p1, p2):
            return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
            
        # Get the attack point that's in the opposite direction from the spider
        attack_point_1 = self.spider_attack_point_1
        attack_point_2 = self.spider_attack_point_2
        
        # Calculate dot products to find which attack point is more opposite to the spider
        def dot_product(a, b):
            return a[0]*b[0] + a[1]*b[1]
            
        # Vectors from character to attack points
        vec1 = (attack_point_1[0] - char_x, attack_point_1[1] - char_y)
        vec2 = (attack_point_2[0] - char_x, attack_point_2[1] - char_y)
        spider_vec = (dx, dy)
        
        # The attack point with the most negative dot product is more opposite to the spider
        dot1 = dot_product(spider_vec, vec1)
        dot2 = dot_product(spider_vec, vec2)
        
        return attack_point_1 if dot1 < dot2 else attack_point_2
        
    def attack_spider(self, initial_spider_pos):
        """Execute the spider attack sequence with continuous attacks.
        
        Args:
            initial_spider_pos: (x, y) coordinates of the spider when first detected
            
        Returns:
            bool: True if attack sequence was completed, False if aborted due to error
        """
        print(f"[SPIDER] Starting attack sequence at {initial_spider_pos}")
        self.spider_attack_in_progress = True
        self.spider_status_var.set("Spider: Attacking...")
        
        # Get the best attack point based on spider position
        attack_point = self.get_best_attack_point(initial_spider_pos)
        if not attack_point:
            print("[SPIDER] No valid attack point found")
            self.spider_status_var.set("Spider: No attack point")
            self.spider_attack_in_progress = False
            return False
            
        print(f"[SPIDER] Attacking from point {attack_point}")
        
        try:
            # Move to attack point and attack
            pydirectinput.moveTo(attack_point[0], attack_point[1], duration=0.1)
            time.sleep(0.1)
            pydirectinput.click(button='left')
            
            # Keep attacking while spider is still in the detection region
            start_time = time.time()
            max_attack_time = 10.0  # Maximum time to spend attacking a single spider
            last_attack_time = time.time()
            
            while time.time() - start_time < max_attack_time:
                # Update status with time remaining
                time_left = max(0, max_attack_time - (time.time() - start_time))
                self.spider_status_var.set(f"Spider: Attacking... ({time_left:.1f}s left)")
                
                # Check if spider is still there
                current_spider = self.check_for_spiders()
                if not current_spider:
                    print("[SPIDER] Spider no longer detected, attack complete")
                    self.spider_status_var.set("Spider: Defeated!")
                    time.sleep(0.5)  # Small delay to show defeated status
                    self.spider_attack_in_progress = False
                    return True
                    
                # Continue attacking (about 2 attacks per second)
                current_time = time.time()
                if current_time - last_attack_time >= 0.5:  # Attack twice per second
                    pydirectinput.click(button='left')
                    last_attack_time = current_time
                
                # Small sleep to prevent CPU overload
                time.sleep(0.05)
                
                # Check if we should abort
                if not self.running:
                    print("[SPIDER] Attack sequence aborted")
                    self.spider_status_var.set("Spider: Attack Aborted")
                    self.spider_attack_in_progress = False
                    return False
                    
            print("[SPIDER] Max attack time reached")
            self.spider_status_var.set("Spider: Attack Timeout")
            time.sleep(0.5)  # Small delay to show timeout status
            self.spider_attack_in_progress = False
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error during spider attack: {e}")
            try:
                # Try to return to character position even if there was an error
                pyautogui.moveTo(self.character_point[0], self.character_point[1], duration=0.2)
            except:
                pass
            return False

    def run_macro(self):
        """Main macro loop based on the new flow.md logic."""
        rock_phases = ['rock_phase_1.png', 'rock_phase_2.png', 'rock_phase_3.png']
        
        self.current_strategy = 1
        phase = 'search' # Can be 'search' or 'mining'

        while self.running:
            try:
                # 1. Determine current strategy
                if self.current_strategy == 1:
                    active_detection_region, active_click_point, strategy_name = \
                        self.detection_region_1, self.click_point_1, "Area 1"
                else: # Strategy 2
                    active_detection_region, active_click_point, strategy_name = \
                        self.detection_region_2, self.click_point_2, "Area 2"

                # Take a screenshot of the active area
                screenshot = pyautogui.screenshot(region=active_detection_region)
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # === SEARCH PHASE (1st phase) ===
                if phase == 'search':
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Searching for rock..."))
                    
                    rock_found_conf, _, _ = self.detect_any_template(screenshot_cv, rock_phases, confidence=self.detection_confidence)
                    
                    if rock_found_conf > 0:
                        # Rock found, switch to mining phase
                        phase = 'mining'
                        self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Rock found. Starting to mine."))
                        self.root.after(0, lambda conf=rock_found_conf: self.confidence_var.set(f"Minable Rock Confidence: {conf:.2f}"))
                        continue
                    else:
                        # No rock found, perform one click as per instructions
                        self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: No rock. Performing speculative click."))
                        pyautogui.click(active_click_point)
                        # Add random variation of ±0.15s to the 0.5s pause (0.35s to 0.65s range)
                        random_delay = 0.5 + random.uniform(-0.15, 0.15)
                        time.sleep(max(0.1, random_delay))  # Ensure minimum 0.1s delay

                        # Search again
                        screenshot = pyautogui.screenshot(region=active_detection_region)
                        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                        rock_found_conf, _, _ = self.detect_any_template(screenshot_cv, rock_phases, confidence=self.detection_confidence)

                        if rock_found_conf > 0:
                            # Rock appeared after the click, switch to mining
                            phase = 'mining'
                            self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Rock appeared. Mining."))
                            continue
                        else:
                            # Still no rock, switch to the next area
                            self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Still no rock. Switching area."))
                            
                            # Calculate new direction (1 or 2)
                            new_direction = 2 if self.current_strategy == 1 else 1
                            
                            print(f"Current: {self.current_strategy}, New: {new_direction}, Last: {self.last_direction}, Count: {self.direction_switches}")
                            
                            # Check if this is a direction switch (not the first time)
                            if self.last_direction is not None and self.last_direction != new_direction:
                                print(f"Direction switch detected! Last: {self.last_direction}, New: {new_direction}")
                                self.direction_switches += 1
                                
                                # Update the UI with the new count
                                self.direction_switches_var.set(f"Direction Switches: {self.direction_switches}")
                                self.root.update_idletasks()  # Force UI update
                                
                                # If we've switched directions twice, wait for the mining delay
                                if self.direction_switches >= 2:
                                    self.status_var.set("Waiting mining delay before continuing...")
                                    self.root.update_idletasks()  # Force UI update
                                    time.sleep(self.mining_retry_timeout)
                                    self.direction_switches = 0  # Reset counter after delay
                                    self.direction_switches_var.set("Direction Switches: 0")
                                    self.root.update_idletasks()  # Force UI update
                                    
                                    # After delay, keep the current direction instead of switching
                                    print(f"After delay, keeping direction: {self.current_strategy}")
                                    self.last_direction = self.current_strategy
                                    phase = 'search'
                                    continue
                            
                            # Update direction tracking for next iteration
                            self.last_direction = new_direction  # Track the direction we're switching to
                            self.current_strategy = new_direction
                            phase = 'search' # Stay in search phase for the new area
                            
                            # Add random variation of ±0.075s to the 1.0s pause (0.925s to 1.075s range)
                            random_switch_delay = 1.0 + random.uniform(-0.075, 0.075)
                            time.sleep(max(0.5, random_switch_delay))  # Ensure minimum 0.5s delay
                            continue

                # === MINING PHASE (2nd phase) ===
                elif phase == 'mining':
                    # Check for minable rocks first (safety check from flow.md)
                    rock_found_conf, _, _ = self.detect_any_template(screenshot_cv, rock_phases, confidence=self.detection_confidence)
                    if rock_found_conf == 0:
                        # Rock disappeared, go back to search phase
                        self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Rock gone. Searching."))
                        phase = 'search'
                        continue
                    self.root.after(0, lambda conf=rock_found_conf: self.confidence_var.set(f"Minable Rock Confidence: {conf:.2f}"))

                    # Perform mining action
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"Mining at {s}..."))
                    pyautogui.click(active_click_point)
                    
                    # Short pause to let game state update before checking for depletion
                    time.sleep(0.5) 
                    if not self.running: break

                    # Check if rock is depleted
                    screenshot = pyautogui.screenshot(region=active_detection_region)
                    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    depleted_conf, _, _ = self.detect_any_template(screenshot_cv, self.mined_rock_templates, confidence=self.detection_confidence)

                    if depleted_conf > 0:
                        # Rock is mined, increment counter
                        self.rock_counter += 1
                        self.root.after(0, lambda: self.rock_counter_var.set(f"Rocks Mined: {self.rock_counter}"))
                        
                        # Check for spiders before switching areas
                        self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Area depleted. Checking for spiders..."))
                        
                        # Check for spiders and attack if found
                        spider_pos = self.check_for_spiders()
                        if spider_pos and self.spider_attack_point_1 and self.spider_attack_point_2:
                            self.attack_spider(spider_pos)
                            # After handling spider, give a moment before continuing
                            time.sleep(0.5)
                        
                        # Check for fire with confidence > 0.5
                        fire_pos = self.detect_fire()
                        if fire_pos is not None:
                            self.root.after(0, lambda: self.status_var.set("Fire detected! Stopping macro for safety."))
                            print("[SAFETY] Fire detected, stopping macro")
                            self.stop_macro()
                            return
                        
                        # Now switch to next detection region
                        self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Switching to next area."))
                        self.current_strategy = 2 if self.current_strategy == 1 else 1
                        phase = 'search' # Go back to searching in the new area
                        time.sleep(self.area_switch_timeout)
                        continue
                    else:
                        # Rock not depleted, wait and repeat mining phase
                        self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Not depleted. Waiting to mine again."))
                        time.sleep(self.mining_retry_timeout)
                        # The loop will continue, and since phase is still 'mining', it will re-run this block.
                        continue

            except Exception as e:
                print(f"Error in macro: {e}")
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                time.sleep(1)

        self.root.after(0, self.stop_macro)

def main():
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = MiningMacroNoSpiders(root)
        
        root.update_idletasks()
        width, height = root.winfo_width(), root.winfo_height()
        x = root.winfo_screenwidth() - width - 20
        y = 20
        root.geometry(f'+{x}+{y}')
        
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
