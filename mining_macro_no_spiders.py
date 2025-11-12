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
        self.click_point_1: Optional[Tuple[int, int]] = None
        self.click_point_2: Optional[Tuple[int, int]] = None
        self.character_point: Optional[Tuple[int, int]] = None
        self.character_marker_id: Optional[int] = None
        self.running: bool = False
        self.overlay = None
        self.asset_status_var = tk.StringVar(value="Checking assets...")
        self.confidence_var = tk.StringVar(value="Confidence: N/A")
        self.current_strategy: int = 1
        
        self.mined_rock_templates = ['rock_phase_4.png', 'rock_phase_4_2.png']
        
        # Relative offsets from character point
        self.relative_mining_offset_1: Optional[Tuple[int, int]] = None
        self.relative_mining_offset_2: Optional[Tuple[int, int]] = None
        
        # Detection confidence
        self.detection_confidence_var = tk.StringVar(value="0.5")
        self.detection_confidence: float = 0.5
        
        # Debug settings
        self.ENABLE_DEBUG = False
        self.debug_screenshot_count = 0
        self.max_debug_screenshots = 5
        self.debug_screenshot_dir = "debug_screenshots"
        if self.ENABLE_DEBUG:
            self.setup_debug_dir()
        
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
            'rock_phase_3_2.png', 'rock_phase_3_3.png', 'rock_phase_4.png', 'rock_phase_4_2.png'
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
        
        confidence_frame = ttk.Frame(self.frame)
        confidence_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(confidence_frame, text="Detection Confidence:").pack(side=tk.LEFT, padx=(0, 5))
        self.confidence_entry = ttk.Entry(confidence_frame, textvariable=self.detection_confidence_var, width=5)
        self.confidence_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.confidence_entry.bind("<FocusOut>", self._validate_detection_confidence)
        self.confidence_entry.bind("<Return>", self._validate_detection_confidence)
        
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self.frame, textvariable=self.status_var, font=('TkDefaultFont', 10, 'bold'), foreground='blue')
        status.pack(pady=(5, 0))

        self.asset_status_label = ttk.Label(self.frame, textvariable=self.asset_status_var, font=('TkDefaultFont', 9), foreground='gray')
        self.asset_status_label.pack(pady=(0, 5))

        confidence_label = ttk.Label(self.frame, textvariable=self.confidence_var, font=('TkDefaultFont', 9), foreground='purple')
        confidence_label.pack(pady=(0, 5))
        
        self.setup_region()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        
    def _validate_detection_confidence(self, event=None):
        """Validate and update the detection confidence."""
        try:
            value = float(self.detection_confidence_var.get())
            if not (0.0 <= value <= 1.0): raise ValueError("Confidence must be 0.0-1.0.")
            self.detection_confidence = value
            self.status_var.set(f"Detection confidence set to {self.detection_confidence:.2f}")
        except ValueError:
            self.detection_confidence_var.set(f"{self.detection_confidence:.2f}")
            self.status_var.set("Invalid confidence. Must be 0.0-1.0.")

    def setup_region(self):
        """Open an overlay to select screen regions."""
        self.reset_selection()

        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.3)
        
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0, cursor='cross', bg='black', bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.selection_phase = 0 # 0: click_1, 1: region_1, 2: click_2, 3: region_2, 4: character
        
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
        if self.selection_phase == 4:
            self.set_character_point(event.x, event.y)

    def set_character_point(self, x, y):
        """Set the character's position."""
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
        """Updates the instruction text on the overlay."""
        instructions = {
            0: "Phase 1/5: Set Mining Click Point 1.\n\nLeft-click your first mining action location.",
            1: "Phase 2/5: Select Detection Area 1.\n\nDrag a rectangle over the first rock's appearance area.",
            2: "Phase 3/5: Set Mining Click Point 2.\n\nLeft-click your second mining action location.",
            3: "Phase 4/5: Select Detection Area 2.\n\nDrag a rectangle over the second rock's appearance area.",
            4: "Phase 5/5: Set Character Position.\n\nRight-click on your character's approximate center.",
            5: "All selections complete!\n\nPress Enter to confirm or Esc to cancel."
        }
        self.canvas.itemconfig(self.instruction_text, text=instructions.get(self.selection_phase, "Unknown phase."))
    
    def confirm_region(self, event=None):
        """Finalize the region and click point selection."""
        if not all([self.click_point_1, self.detection_region_1, self.click_point_2, self.detection_region_2, self.character_point]):
            self.status_var.set("Error: All 5 phases must be completed.")
            return
            
        if self.character_point:
            self.relative_mining_offset_1 = (self.click_point_1[0] - self.character_point[0], self.click_point_1[1] - self.character_point[1])
            self.relative_mining_offset_2 = (self.click_point_2[0] - self.character_point[0], self.click_point_2[1] - self.character_point[1])
        else:
            self.status_var.set("Error: Character point not set.")
            return
            
        self.cleanup_overlay()
        self.status_var.set("Ready to start")
        self.start_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
    
    def clear_overlay_elements(self):
        """Clear visual elements from the overlay."""
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            for tag in ['selection', 'click_point', 'character_point', 'instruction']:
                self.canvas.delete(tag)

    def reset_selection(self):
        """Reset the current selection and state."""
        self.clear_overlay_elements()
        self.selection_phase = 0
        
        self.click_point_1, self.click_point_2 = None, None
        self.detection_region_1, self.detection_region_2 = None, None
        self.character_point = None

        self.click_marker_ids = []
        self.character_marker_id = None
        self.detection_region_1_rect_id, self.detection_region_2_rect_id = None, None
        
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
        """Clean up the overlay window."""
        if hasattr(self, 'overlay') and self.overlay:
            try:
                self.overlay.grab_release()
                self.overlay.destroy()
            except tk.TclError: pass
            self.overlay = None

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

    def run_macro(self):
        """Main macro loop with constant detection."""
        rock_phases = ['rock_phase_1.png', 'rock_phase_2.png', 'rock_phase_3.png', 'rock_phase_3_2.png', 'rock_phase_3_3.png']
        
        self.current_strategy = 1
        
        while self.running:
            try:
                # 1. Determine current strategy
                if self.current_strategy == 1:
                    active_detection_region, active_click_point, strategy_name = \
                        self.detection_region_1, self.click_point_1, "Area 1"
                else: # Strategy 2
                    active_detection_region, active_click_point, strategy_name = \
                        self.detection_region_2, self.click_point_2, "Area 2"

                self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Checking area..."))
                screenshot = pyautogui.screenshot(region=active_detection_region)
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # 2. PRIORITY 1: Check for a depleted rock (phase 4) to trigger an immediate switch
                depleted_conf, _, _ = self.detect_any_template(screenshot_cv, self.mined_rock_templates, confidence=self.detection_confidence)
                if depleted_conf > 0:
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Area depleted. Switching."))
                    self.current_strategy = 2 if self.current_strategy == 1 else 1
                    time.sleep(0.5)
                    continue

                # 3. PRIORITY 2: If not depleted, search for a minable rock up to 3 times
                rock_found = False
                for i in range(3):
                    if not self.running: break
                    self.root.after(0, lambda s=strategy_name, c=i+1: self.status_var.set(f"{s}: Searching... ({c}/3)"))
                    
                    screenshot = pyautogui.screenshot(region=active_detection_region)
                    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    rock_found_conf, _, _ = self.detect_any_template(screenshot_cv, rock_phases, confidence=self.detection_confidence)

                    if rock_found_conf > 0:
                        rock_found = True
                        break
                    
                    time.sleep(0.5) # Wait between failed checks

                # 4. Act based on the search result
                if rock_found:
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"Mining at {s}..."))
                    # === REALTIME MINING SUB-LOOP with safety break ===
                    max_mine_attempts = 3
                    for attempt in range(max_mine_attempts):
                        if not self.running: break

                        pyautogui.click(active_click_point)
                        
                        # Update status to show mining attempt
                        self.root.after(0, lambda c=attempt + 1: self.status_var.set(f"Mining... (attempt {c}/{max_mine_attempts})"))
                        time.sleep(1.0)

                        # Check if the rock is now depleted
                        mine_check_shot = pyautogui.screenshot(region=active_detection_region)
                        mine_check_cv = cv2.cvtColor(np.array(mine_check_shot), cv2.COLOR_RGB2BGR)
                        depleted_conf, _, _ = self.detect_any_template(mine_check_cv, self.mined_rock_templates, confidence=self.detection_confidence)
                        
                        # Update confidence score in UI
                        self.root.after(0, lambda conf=depleted_conf: self.confidence_var.set(f"Depleted Confidence: {conf:.2f}"))

                        if depleted_conf > 0:
                            self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s} depleted. Switching."))
                            break
                    else: # This runs if the for loop completes without a break
                        self.root.after(0, lambda: self.status_var.set("Mining timeout. Switching anyway."))
                    # === END MINING SUB-LOOP ===

                    # After mining (successful or timeout), switch area and continue main loop
                    self.current_strategy = 2 if self.current_strategy == 1 else 1
                    time.sleep(0.5)
                    continue
                
                else: # Rock not found after 3 checks
                    self.root.after(0, lambda s=strategy_name: self.status_var.set(f"{s}: Not found. Switching area."))
                    self.current_strategy = 2 if self.current_strategy == 1 else 1
                    time.sleep(1.0) # Longer pause after a total failure
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
