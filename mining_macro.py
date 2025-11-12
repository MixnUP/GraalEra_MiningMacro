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

class MiningMacro:
    def __init__(self, root):
        """Initialize the mining macro application."""
        self.root = root
        self.root.title("Mining Macro")
        
        # State
        self.detection_region_1: Optional[Tuple[int, int, int, int]] = None
        self.detection_region_2: Optional[Tuple[int, int, int, int]] = None
        self.click_point_1: Optional[Tuple[int, int]] = None
        self.click_point_2: Optional[Tuple[int, int]] = None
        self.attack_point_1: Optional[Tuple[int, int]] = None # New attack point 1
        self.attack_point_2: Optional[Tuple[int, int]] = None # New attack point 2
        self.character_point: Optional[Tuple[int, int]] = None
        self.character_marker_id: Optional[int] = None
        self.spider_region: Optional[Tuple[int, int, int, int]] = None
        self.spider_region_rect_id: Optional[int] = None
        self.spider_region_start: Optional[Tuple[int, int]] = None
        self.running: bool = False
        self.overlay = None
        self.asset_status_var = tk.StringVar(value="Checking assets...") # New asset status variable
        self.confidence_var = tk.StringVar(value="Confidence: N/A") # New real-time confidence variable
        self.current_strategy: int = 1 # 1 for pair 1, 2 for pair 2
        
        self.mined_rock_templates = ['rock_phase_4.png', 'rock_phase_4_2.png'] # Define as class attribute
        
        # Relative offsets from character point
        self.relative_mining_offset_1: Optional[Tuple[int, int]] = None
        self.relative_mining_offset_2: Optional[Tuple[int, int]] = None
        self.relative_attack_offset_1: Optional[Tuple[int, int]] = None
        self.relative_attack_offset_2: Optional[Tuple[int, int]] = None
        
        # Mining specific state
        self.mining_delay_var = tk.StringVar(value="12.0")  # Default mining delay in seconds
        self.mining_delay: float = 12.0  # Default value (12 seconds)

        # Detection confidence (0.0 to 1.0, lower = more sensitive)
        self.detection_confidence_var = tk.StringVar(value="0.5")  # Default detection confidence
        self.detection_confidence: float = 0.5  # Default value (0.5 is more permissive)
        
        # Debug settings
        # To enable debug mode, set ENABLE_DEBUG to True
        self.ENABLE_DEBUG = False  # Set to True to enable debug screenshots
        self.debug_screenshot_count = 0
        self.max_debug_screenshots = 5  # Max screenshots per session
        self.debug_screenshot_dir = "debug_screenshots"
        if self.ENABLE_DEBUG:
            self.setup_debug_dir()
        
        # Create minimal UI
        self.create_ui()
        
        # Check assets after UI is created
        self._check_assets_loaded()
        
        # Make window stay on top and small
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
    
    def setup_debug_dir(self):
        """Create debug directory if it doesn't exist."""
        os.makedirs(self.debug_screenshot_dir, exist_ok=True)
        
    def save_debug_screenshot(self, screenshot, prefix="debug", confidence=0.0):
        """
        Save a screenshot with debug information.
        
        Args:
            screenshot: The OpenCV image to save
            prefix: Prefix for the filename
            confidence: Detection confidence score (0.0-1.0)
            
        Note: Enable debug mode by setting ENABLE_DEBUG = True in __init__
        """
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
            'rock_phase_1.png', 'rock_phase_2.png', 'rock_phase_3.png', 'rock_phase_3_2.png', 'rock_phase_3_3.png', 'rock_phase_4.png', 'rock_phase_4_2.png',
            'spider1.png', 'spider2.png', 'spider3.png'
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
            self.start_btn.config(state=tk.DISABLED) # Disable start if assets fail
            self.reset_btn.config(state=tk.DISABLED) # Disable reset if assets fail
        
        return all_loaded
    
    def create_ui(self):
        """Create the main UI components."""
        # Main frame with minimal padding
        self.frame = ttk.Frame(self.root, padding="5")
        self.frame.pack(padx=5, pady=5)
        
        # Control buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.start_btn = ttk.Button(
            btn_frame, 
            text="Start", 
            command=self.start_macro,
            width=8,
            state=tk.DISABLED # Initially disabled
        )
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(
            btn_frame,
            text="Stop",
            command=self.stop_macro,
            state=tk.DISABLED,
            width=8
        )
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.reset_btn = ttk.Button(
            btn_frame,
            text="Reset Selection",
            command=self.setup_region,
            width=15,
            state=tk.DISABLED # Initially disabled
        )
        self.reset_btn.pack(side=tk.LEFT, padx=2)
        
        # Mining Delay Input
        delay_frame = ttk.Frame(self.frame)
        delay_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(delay_frame, text="Mining Delay (s):").pack(side=tk.LEFT, padx=(0, 5))
        self.delay_entry = ttk.Entry(
            delay_frame,
            textvariable=self.mining_delay_var,
            width=5
        )
        self.delay_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.delay_entry.bind("<FocusOut>", self._validate_mining_delay)
        self.delay_entry.bind("<Return>", self._validate_mining_delay)
        
        # Detection Confidence Input
        confidence_frame = ttk.Frame(self.frame)
        confidence_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(confidence_frame, text="Detection Confidence:").pack(side=tk.LEFT, padx=(0, 5))
        self.confidence_entry = ttk.Entry(
            confidence_frame,
            textvariable=self.detection_confidence_var,
            width=5
        )
        self.confidence_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.confidence_entry.bind("<FocusOut>", self._validate_detection_confidence)
        self.confidence_entry.bind("<Return>", self._validate_detection_confidence)
        
        # Status label (minimal)
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(
            self.frame,
            textvariable=self.status_var,
            font=('TkDefaultFont', 10, 'bold'),
            foreground='blue'
        )
        status.pack(pady=(5, 0))

        # Asset Status Label
        self.asset_status_label = ttk.Label( # Store reference to the label
            self.frame,
            textvariable=self.asset_status_var,
            font=('TkDefaultFont', 9),
            foreground='gray'
        )
        self.asset_status_label.pack(pady=(0, 5))

        # Real-time Confidence Label
        confidence_label = ttk.Label(
            self.frame,
            textvariable=self.confidence_var,
            font=('TkDefaultFont', 9),
            foreground='purple'
        )
        confidence_label.pack(pady=(0, 5))
        
        # Start with region selection
        self.setup_region()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        
    def _validate_mining_delay(self, event=None):
        """Validate and update the mining delay from the input field."""
        try:
            value = float(self.mining_delay_var.get())
            if value <= 0:
                raise ValueError("Delay must be positive.")
            self.mining_delay = value
            self.status_var.set(f"Mining delay set to {self.mining_delay:.1f}s")
        except ValueError:
            self.mining_delay_var.set(f"{self.mining_delay:.1f}") # Revert to last valid
            self.status_var.set("Invalid delay. Must be a positive number.")

    def _validate_detection_confidence(self, event=None):
        """Validate and update the detection confidence from the input field."""
        try:
            value = float(self.detection_confidence_var.get())
            if not (0.0 <= value <= 1.0):
                raise ValueError("Confidence must be between 0.0 and 1.0.")
            self.detection_confidence = value
            self.status_var.set(f"Detection confidence set to {self.detection_confidence:.2f}")
        except ValueError:
            self.detection_confidence_var.set(f"{self.detection_confidence:.2f}") # Revert to last valid
            self.status_var.set("Invalid confidence. Must be a number between 0.0 and 1.0.")

    def setup_region(self):
        """Open a transparent overlay to select the screen region."""
        self.reset_selection() # Ensure a clean slate for new selection

        # Create overlay window
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.3)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.overlay,
            highlightthickness=0,
            cursor='cross',
            bg='black',
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # --- New Selection State ---
        self.selection_start = None
        self.selection_phase = 0 # 0: click_point_1, 1: detection_region_1, 2: click_point_2, 3: detection_region_2, 4: character_point, 5: attack_point_1, 6: attack_point_2, 7: spider_region
        
        self.detection_region_1_start = None
        self.detection_region_1_rect_id = None
        self.detection_region_2_start = None
        self.detection_region_2_rect_id = None
        
        self.click_point_1 = None
        self.click_point_2 = None
        self.click_marker_ids = []
        self.character_point = None
        self.character_marker_id = None
        self.spider_region_start = None
        self.spider_region_rect_id = None
        
        # Instructions
        screen_width = self.overlay.winfo_screenwidth()
        self.instruction_text = self.canvas.create_text(
            screen_width // 2, 30,
            text="", # Will be set by update_instructions
            fill="white",
            font=('Arial', 12, 'bold'),
            anchor='center',
            justify='center',
            tags='instruction'
        )
        self.update_instructions() # Set initial instruction
        
        # Bind events
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<Button-3>', self.on_right_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.overlay.bind('<Escape>', self.cancel_selection)
        self.overlay.bind('<Return>', self.confirm_region)
        
        self.overlay.grab_set()
        
    def on_click(self, event):
        """Handle mouse clicks for region and click point selection."""
        if self.selection_phase == 0: # Click point 1
            self.set_click_point(event.x, event.y, 'mining_1')
        elif self.selection_phase == 1: # Detection region 1
            if self.detection_region_1_rect_id is None:
                self.detection_region_1_start = (event.x, event.y)
        elif self.selection_phase == 2: # Click point 2
            self.set_click_point(event.x, event.y, 'mining_2')
        elif self.selection_phase == 3: # Detection region 2
            if self.detection_region_2_rect_id is None:
                self.detection_region_2_start = (event.x, event.y)
        elif self.selection_phase == 5: # Attack point 1
            self.set_click_point(event.x, event.y, 'attack_1')
        elif self.selection_phase == 6: # Attack point 2
            self.set_click_point(event.x, event.y, 'attack_2')
        elif self.selection_phase == 7: # Spider region
            if self.spider_region_rect_id is None:
                self.spider_region_start = (event.x, event.y)
    
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
        elif self.selection_phase == 7: # Spider region
            if not self.spider_region_start: return
            x1, y1 = self.spider_region_start
            x2, y2 = event.x, event.y
            if self.spider_region_rect_id: self.canvas.coords(self.spider_region_rect_id, x1, y1, x2, y2)
            else: self.spider_region_rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline='yellow', fill='red', stipple='gray50', width=2, tags='spider_selection')

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
        elif self.selection_phase == 7: # Spider region
            if not (self.spider_region_start and self.spider_region_rect_id): return
            x1, y1, x2, y2 = self.canvas.coords(self.spider_region_rect_id)
            if abs(x2 - x1) < 20 or abs(y2 - y1) < 20: self.status_var.set("Selection too small."); return
            self.spider_region = (int(min(x1, x2)), int(min(y1, y2)), int(abs(x2 - x1)), int(abs(y2 - y1)))
            self.selection_phase = 8 # All selections done
            self.update_instructions()

    def set_click_point(self, x, y, point_type):
        """Set the click point and update the marker."""
        if point_type == 'mining_1':
            self.click_point_1 = (x, y)
            self.draw_click_marker(x, y, 'cyan', 'mining_1')
            self.selection_phase = 1
            self.update_instructions()
        elif point_type == 'mining_2':
            self.click_point_2 = (x, y)
            self.draw_click_marker(x, y, 'lime', 'mining_2')
            self.selection_phase = 3
            self.update_instructions()
        elif point_type == 'attack_1':
            self.attack_point_1 = (x, y)
            self.draw_click_marker(x, y, 'orange', 'attack_1')
            self.selection_phase = 6
            self.update_instructions()
        elif point_type == 'attack_2':
            self.attack_point_2 = (x, y)
            self.draw_click_marker(x, y, 'magenta', 'attack_2')
            self.selection_phase = 7
            self.update_instructions()

    def draw_click_marker(self, x, y, color, tag):
        """Draws a marker for a click point and manages existing ones."""
        # Clear previous markers with the same primary tag (e.g., 'mining_1')
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
        if self.selection_phase == 4: # Character position
            self.set_character_point(event.x, event.y)

    def set_character_point(self, x, y):
        """Set the character's position and update the marker."""
        self.character_point = (x, y)
        if self.character_marker_id: self.canvas.delete(self.character_marker_id)
        size = 7
        self.character_marker_id = self.canvas.create_rectangle(
            x - size, y - size, x + size, y + size,
            outline='red', fill='red', stipple='gray25', width=2, tags='character_point'
        )
        self.selection_phase = 5
        self.update_instructions()
    
    def update_instructions(self):
        """Updates the instruction text on the overlay based on the current selection phase."""
        instructions = {
            0: "Phase 1/8: Set Mining Click Point 1.\n\nLeft-click the location for your first mining action (e.g., a keybind).",
            1: "Phase 2/8: Select Detection Area 1.\n\nDrag a rectangle over the area where a rock appears after using Click Point 1.",
            2: "Phase 3/8: Set Mining Click Point 2.\n\nLeft-click the location for your second mining action.",
            3: "Phase 4/8: Select Detection Area 2.\n\nDrag a rectangle over the area where a rock appears after using Click Point 2.",
            4: "Phase 5/8: Set Character Position.\n\nRight-click on your character's approximate center.",
            5: "Phase 6/8: Set Attack Click Point 1.\n\nLeft-click your primary attack keybind location.",
            6: "Phase 7/8: Set Attack Click Point 2.\n\nLeft-click your secondary attack keybind location.",
            7: "Phase 8/8: Select Spider Watch Region.\n\nDrag a rectangle over the area to monitor for spiders.",
            8: "All selections complete!\n\nPress Enter to confirm or Esc to cancel."
        }
        self.canvas.itemconfig(self.instruction_text, text=instructions.get(self.selection_phase, "Unknown phase."))
    
    def confirm_region(self, event=None):
        """Finalize the region and click point selection."""
        if not all([self.click_point_1, self.detection_region_1, self.click_point_2, self.detection_region_2,
                    self.character_point, self.attack_point_1, self.attack_point_2, self.spider_region]):
            self.status_var.set("Error: All 8 phases must be completed.")
            return
            
        # Calculate relative offsets after all points are confirmed
        if self.character_point:
            self.relative_mining_offset_1 = (self.click_point_1[0] - self.character_point[0], self.click_point_1[1] - self.character_point[1])
            self.relative_mining_offset_2 = (self.click_point_2[0] - self.character_point[0], self.click_point_2[1] - self.character_point[1])
            self.relative_attack_offset_1 = (self.attack_point_1[0] - self.character_point[0], self.attack_point_1[1] - self.character_point[1])
            self.relative_attack_offset_2 = (self.attack_point_2[0] - self.character_point[0], self.attack_point_2[1] - self.character_point[1])
        else:
            self.status_var.set("Error: Character point not set, cannot calculate offsets.")
            return
            
        self.cleanup_overlay()
        self.status_var.set("Ready to start")
        self.start_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
    
    def clear_overlay_elements(self): 
        """Clear only the visual elements from the overlay."""
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            for tag in ['selection', 'click_point', 'character_point', 'spider_selection', 'instruction']:
                self.canvas.delete(tag)

    def reset_selection(self):
        """Reset the current selection and its state variables."""
        self.clear_overlay_elements()
        self.selection_start = None
        self.selection_phase = 0
        
        self.click_point_1 = None
        self.click_point_2 = None
        self.detection_region_1 = None
        self.detection_region_2 = None
        self.attack_point_1 = None
        self.attack_point_2 = None
        self.spider_region = None
        self.character_point = None

        self.click_marker_ids = []
        self.character_marker_id = None
        self.detection_region_1_rect_id = None
        self.detection_region_2_rect_id = None
        self.spider_region_rect_id = None
        
        self.status_var.set("Ready")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        
        if hasattr(self, 'overlay') and self.overlay:
            self.update_instructions()

    def cancel_selection(self, event=None):
        """Cancel the selection process and reset state."""
        self.cleanup_overlay()
        self.reset_selection()

    def cleanup_overlay(self):
        """Clean up the overlay window."""
        if hasattr(self, 'overlay') and self.overlay:
            try:
                self.overlay.grab_release()
                self.overlay.destroy()
            except tk.TclError:
                pass
            self.overlay = None


    
    def start_macro(self):
        """Start the mining macro."""
        if not all([self.detection_region_1, self.detection_region_2, self.click_point_1, self.click_point_2,
                    self.character_point, self.attack_point_1, self.attack_point_2, self.spider_region]):
            self.status_var.set("Error: All 8 setup phases not complete. Please reset and select again.")
            return
            
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.DISABLED)
        self.status_var.set("Running...")
        
        # Start the macro in a separate thread
        self.macro_thread = threading.Thread(target=self.run_macro, daemon=True)
        self.macro_thread.start()
    
    def stop_macro(self):
        """Stop the mining macro."""
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.NORMAL)
        self.status_var.set("Stopped")


    
    def detect_any_template(self, screenshot, templates, confidence=0.7):
        """
        Detect if any of the templates match in the screenshot.
        Returns the highest confidence value found, its location (top-left), and the template's size (width, height).
        Returns (0.0, None, None) if no match meets the threshold.
        """
        best_match_val = 0.0
        best_match_loc = None
        best_match_template_size = None # (width, height)
        best_template_name = None # For debug logging
        
        for template_file in templates:
            try:
                template_path = resource_path(f'assets/{template_file}')
                template = cv2.imread(template_path)
                if template is None:
                    print(f"[WARN] Could not load template: {template_file}")
                    continue
                
                # Check if template is larger than screenshot
                if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
                    print(f"[WARN] Template {template_file} is larger than screenshot")
                    continue
                
                # Perform template matching
                result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                # Debug: Visualize template matching results when debug mode is enabled
                # Shows where the template is being matched and the confidence score
                if self.ENABLE_DEBUG and max_val < confidence and self.debug_screenshot_count < self.max_debug_screenshots:
                    debug_img = screenshot.copy()
                    h, w = template.shape[:2]
                    top_left = max_loc
                    bottom_right = (top_left[0] + w, top_left[1] + h)
                    cv2.rectangle(debug_img, top_left, bottom_right, (0, 0, 255), 2)  # Red rectangle around match
                    cv2.putText(debug_img, f"{template_file}: {max_val:.2f}", 
                              (top_left[0], top_left[1]-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)  # Confidence text
                    self.save_debug_screenshot(debug_img, f"template_{template_file.replace('.png', '')}", max_val)
                
                if max_val > best_match_val:
                    best_match_val = max_val
                    best_match_loc = max_loc
                    best_match_template_size = (template.shape[1], template.shape[0]) # (width, height)
                    best_template_name = template_file # Store template name for debug log
            
            except Exception as e:
                print(f"[ERROR] Error processing template {template_file}: {e}")
                continue
        
        # Log the best match found (only in debug mode)
        if self.ENABLE_DEBUG:
            if best_match_val > 0:
                print(f"[DEBUG] Best match: {best_template_name} with confidence: {best_match_val:.2f} at {best_match_loc}")
            else:
                print("[DEBUG] No template matched above confidence threshold")
                if self.debug_screenshot_count < self.max_debug_screenshots:
                    self.save_debug_screenshot(screenshot, "no_match", 0.0)
        
        return (best_match_val, best_match_loc, best_match_template_size) if best_match_val > confidence else (0.0, None, None)

    def _check_and_attack_spiders(self, spider_templates):
        """Scans for spiders and attacks them until they are gone."""
        if not self.spider_region or len(self.spider_region) < 4:
            self.root.after(0, lambda: self.status_var.set("Error: Spider region not set"))
            return 0.0
            
        self.root.after(0, lambda: self.status_var.set("Checking for spiders..."))
        
        spider_check_duration = 3  # seconds to initially check for spiders
        spider_check_start_time = time.time()
        spider_detected_confidence = 0.0
        
        # Get spider region dimensions
        region_x, region_y, region_w, region_h = self.spider_region
        
        # Initial brief check for spiders
        while self.running and (time.time() - spider_check_start_time < spider_check_duration):
            try:
                # Take screenshot of spider region
                spider_screenshot = pyautogui.screenshot(region=self.spider_region)
                spider_screenshot_cv = cv2.cvtColor(np.array(spider_screenshot), cv2.COLOR_RGB2BGR)
                
                # Check if spider region is too small for templates
                if region_w < 30 or region_h < 30:  # Minimum reasonable size for detection
                    self.root.after(0, lambda: self.status_var.set("Spider region too small"))
                    return 0.0
                
                # Check for spiders
                spider_detected_confidence, _, _ = self.detect_any_template(
                    spider_screenshot_cv, 
                    spider_templates, 
                    confidence=self.detection_confidence
                )
                
                self.root.after(0, lambda conf=spider_detected_confidence: 
                    self.confidence_var.set(f"Spider Confidence: {conf:.2f}"))
                
                if spider_detected_confidence > 0:
                    self.root.after(0, lambda: self.status_var.set("Spider detected! Attacking..."))
                    break
                    
            except Exception as e:
                print(f"[ERROR] Error during spider detection: {e}")
                break
                
            time.sleep(0.1)
            
            # Persistently attack until spider is gone
            while self.running and spider_detected_confidence > 0.0:
                # Alternate attack points
                attack_point = self.attack_point_1 if random.random() < 0.5 else self.attack_point_2
                pyautogui.click(attack_point)
                time.sleep(0.5)  # Delay between attacks

                # Re-check for spiders
                spider_screenshot = pyautogui.screenshot(region=self.spider_region)
                spider_screenshot_cv = cv2.cvtColor(np.array(spider_screenshot), cv2.COLOR_RGB2BGR)
                spider_detected_confidence, _, _ = self.detect_any_template(spider_screenshot_cv, spider_templates, confidence=self.detection_confidence)
                self.root.after(0, lambda conf=spider_detected_confidence: self.confidence_var.set(f"Spider Confidence: {conf:.2f}"))

            self.root.after(0, lambda: self.status_var.set("Spider defeated!"))
        else:
            self.root.after(0, lambda: self.status_var.set("No spiders detected."))

    def run_macro(self):
        """Main macro loop using directional strategy."""
        rock_phases = ['rock_phase_1.png', 'rock_phase_2.png', 'rock_phase_3.png', 'rock_phase_3_2.png', 'rock_phase_3_3.png']
        spider_templates = ['spider1.png', 'spider2.png', 'spider3.png']
        
        # Reset strategy to 1 each time macro starts
        self.current_strategy = 1
        consecutive_failures = 0
        
        while self.running:
            try:
                # 1. Determine current strategy's regions and click points
                if self.current_strategy == 1:
                    active_detection_region = self.detection_region_1
                    active_click_point = self.click_point_1
                    fallback_click_point = self.click_point_2
                    strategy_name = "Strategy 1"
                else: # Strategy 2
                    active_detection_region = self.detection_region_2
                    active_click_point = self.click_point_2
                    fallback_click_point = self.click_point_1
                    strategy_name = "Strategy 2"

                # 2. Search for a rock in the active detection area
                self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Searching for rock..."))
                screenshot = pyautogui.screenshot(region=active_detection_region)
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                rock_found_confidence, _, _ = self.detect_any_template(screenshot_cv, rock_phases, confidence=self.detection_confidence)
                self.root.after(0, lambda conf=rock_found_confidence: self.confidence_var.set(f"Rock Confidence: {conf:.2f}"))

                # 3. Decide whether to perform a targeted click or a blind "cross-click"
                click_point_to_use = active_click_point
                if rock_found_confidence > 0:
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Rock found. Clicking."))
                    pyautogui.click(click_point_to_use)
                else:
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: No rock. Blind cross-click."))
                    pyautogui.click(fallback_click_point)
                    click_point_to_use = fallback_click_point # For accurate status/debug if needed

                rock_was_mined_successfully = False
                
                # Continuous monitoring for rock state changes
                self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Monitoring rock state..."))
                
                # Variables for continuous monitoring
                check_interval = 0.2  # seconds between checks
                max_checks = int(self.mining_delay * 5)  # Check more frequently than mining delay
                checks_done = 0
                rock_was_mined_successfully = False
                rock_mined_confirmed = False
                
                # Check for mined rock continuously until mined or timeout
                while checks_done < max_checks and self.running and not rock_was_mined_successfully:
                    # Take a screenshot and check for mined rock
                    screenshot = pyautogui.screenshot(region=active_detection_region)
                    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    
                    # Check for mined rock
                    mined_rock_confidence, _, _ = self.detect_any_template(
                        screenshot_cv, 
                        self.mined_rock_templates, 
                        confidence=self.detection_confidence
                    )
                    
                    # Update UI with current confidence
                    self.root.after(0, lambda conf=mined_rock_confidence: 
                        self.confidence_var.set(f"Mining Confidence: {conf:.2f}"))
                    
                    if mined_rock_confidence > 0.0:
                        if not rock_mined_confirmed:
                            # First detection of mined rock
                            rock_mined_confirmed = True
                            self.root.after(0, lambda s=strategy_name: 
                                self.status_var.set(f"{s}: Rock mined! Checking for spiders..."))
                            # Check for spiders now that we've confirmed the rock is mined
                            self._check_and_attack_spiders(spider_templates)
                            # Consider the mining successful after spider check
                            rock_was_mined_successfully = True
                            break
                    
                    checks_done += 1
                    time.sleep(check_interval)
                
                if not rock_was_mined_successfully:
                    self.root.after(0, lambda s=strategy_name: 
                        self.status_var.set(f"{s}: Rock not mined after monitoring period."))

                # Update consecutive failures based on overall success
                if rock_was_mined_successfully:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

                # 6. Check for too many consecutive failures
                if consecutive_failures >= 4: # Increased threshold for more tolerance
                    self.root.after(0, lambda: self.status_var.set("Position Lost! Please Reset."))
                    self.root.after(0, self.stop_macro)
                    break

                # 7. Switch to the other strategy for the next cycle
                self.current_strategy = 2 if self.current_strategy == 1 else 1
                
                # Brief pause before next cycle
                time.sleep(0.5)

            except Exception as e:
                print(f"Error in macro: {e}")
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                time.sleep(1)

        # Clean up when stopped
        self.root.after(0, self.stop_macro)

def main():
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = MiningMacro(root)
        
        # Set window position (top-right corner)
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = root.winfo_screenwidth() - width - 20
        y = 20
        root.geometry(f'+{x}+{y}')
        
        # Start the application
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
