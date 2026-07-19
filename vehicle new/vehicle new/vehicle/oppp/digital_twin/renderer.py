"""
Interactive Open3D GUI and PBR renderer for the Coke Can digital twin.
Supports live marker placement, physical dent deforming, camera presets,
frustum overlays, animations, and inspection reports.
"""
import time
import threading
import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
from typing import List, Dict, Tuple

from .config import CAN_HEIGHT, CAN_BODY_RADIUS, DIET_COKE_RED
from .model import generate_digital_twin, generate_can_mesh, generate_pull_tab_mesh
from .mapper import CanSurfaceMapper
from .materials import get_aluminum_material, get_marker_material, get_glow_material
from .marker import (
    DefectMarker, generate_sphere_marker, generate_scratch_geometry,
    deform_mesh_for_dent, apply_heatmap_to_mesh, paint_scratch_on_mesh
)
from .camera import InspectionCamera

class InspectionRenderer:
    """
    Main Application Window integrating the 3D viewport, sidebar controls,
    multi-camera simulation, and real-time defect monitoring.
    """
    def __init__(self, mapper: CanSurfaceMapper):
        self.mapper = mapper
        self.active_defects: Dict[str, DefectMarker] = {}
        self.defect_counter = 0
        self.elapsed_time = 0.0
        self.show_camera_rig = False
        
        # Load geometries
        self.base_can_mesh = generate_can_mesh()
        self.pull_tab_mesh = generate_pull_tab_mesh()
        self.can_body_mesh = generate_can_mesh()  # Deformable version
        
        import platform
        import os
        is_windows_arm = "ARM64" in platform.machine().upper() and platform.system() == "Windows"
        self.headless = (is_windows_arm and os.environ.get("FORCE_GUI") != "true") or os.environ.get("FORCE_HEADLESS") == "true"
        
        # Load geometries
        self.base_can_mesh = generate_can_mesh()
        self.pull_tab_mesh = generate_pull_tab_mesh()
        self.can_body_mesh = generate_can_mesh()  # Deformable version
        
        if self.headless:
            print("[InspectionRenderer] Snapdragon/ARM64 platform detected. Software OpenGL GUI rendering bypassed. Digital Twin model engine is active.")
            self.app = None
            self.window = None
            self.scene_widget = None
            self.sidebar = None
            self.running = True
            return
            
        # Initialize GUI App
        self.app = gui.Application.instance
        self.app.initialize()
        
        # Create Window
        self.window = self.app.create_window("Coke Can Inspection - Digital Twin", 1400, 850)
        self.window.set_on_layout(self._on_layout)
        self.window.set_on_close(self._on_close)
        
        # 3D Scene Widget
        self.scene_widget = gui.SceneWidget()
        self.scene_widget.scene = rendering.Open3DScene(self.window.renderer)
        self.scene_widget.scene.set_background_color([0.08, 0.08, 0.1, 1.0])
        
        # Setup Camera
        self.scene_widget.setup_camera(45.0, self.scene_widget.scene.bounding_box, [0, 0, 0])
        self._set_camera_preset("Front")
        
        # Setup PBR Lighting
        self._setup_lighting()
        
        # Setup Materials
        self.aluminum_material = get_aluminum_material()
        
        # Add Can to Scene
        self._refresh_can_mesh()
        
        # Build Multi-camera inspection rig
        self._init_camera_rig()
        
        # Build Sidebar
        self._build_sidebar()
        
        # Add to window
        self.window.add_child(self.scene_widget)
        self.window.add_child(self.sidebar)
        
        # Start Animation Thread
        self.running = True
        self.animation_thread = threading.Thread(target=self._animation_loop, daemon=True)
        self.animation_thread.start()


    def _setup_lighting(self):
        """Sets up studio-quality lighting for aluminum visualization."""
        scene = self.scene_widget.scene.scene
        scene.enable_sun_light(True)
        # Main key light
        scene.set_sun_light([-1.0, -1.0, -1.0], [1.0, 1.0, 1.0], 80000.0)
        # Ambient/indirect light
        scene.enable_indirect_light(True)
        scene.set_indirect_light_intensity(35000.0)

    def _init_camera_rig(self):
        """Initializes the multi-camera layout around the can."""
        h2 = CAN_HEIGHT / 2.0
        # 4 orthogonal cameras around the body, 1 top, 1 bottom
        self.rig_cameras = [
            InspectionCamera("Cam_Front", (0.0, -0.22, 0.0), lookat=(0.0, 0.0, 0.0)),
            InspectionCamera("Cam_Back", (0.0, 0.22, 0.0), lookat=(0.0, 0.0, 0.0)),
            InspectionCamera("Cam_Left", (-0.22, 0.0, 0.0), lookat=(0.0, 0.0, 0.0)),
            InspectionCamera("Cam_Right", (0.22, 0.0, 0.0), lookat=(0.0, 0.0, 0.0)),
            InspectionCamera("Cam_Top", (0.0, 0.0, 0.22), up=(0.0, 1.0, 0.0)),
            InspectionCamera("Cam_Bottom", (0.0, 0.0, -0.22), up=(0.0, -1.0, 0.0))
        ]

    def _refresh_can_mesh(self):
        """Re-adds the combined can and pull-tab mesh to the scene."""
        if self.headless:
            return
        if self.scene_widget.scene.has_geometry("can_body"):
            self.scene_widget.scene.remove_geometry("can_body")
            
        combined_mesh = self.can_body_mesh + self.pull_tab_mesh
        combined_mesh.compute_vertex_normals()
        self.scene_widget.scene.add_geometry("can_body", combined_mesh, self.aluminum_material)

    def _build_sidebar(self):
        """Constructs the sidebar panel UI."""
        self.sidebar = gui.Vert(4, gui.Margins(12, 12, 12, 12))
        
        # --- TITLE ---
        title_label = gui.Label("COKE CAN DIGITAL TWIN")
        title_label.text_color = gui.Color(0.9, 0.9, 0.9)
        self.sidebar.add_child(title_label)
        
        # Separator line
        self.sidebar.add_child(gui.Label("------------------------------------------------"))
        
        # --- INSPECTION STATUS ---
        status_header = gui.Label("INSPECTION REPORT")
        self.sidebar.add_child(status_header)
        
        self.status_badge = gui.Label("STATUS: PASS")
        self.status_badge.text_color = gui.Color(0.2, 0.9, 0.2) # green
        self.sidebar.add_child(self.status_badge)
        
        self.sidebar.add_child(gui.Label("------------------------------------------------"))
        
        # --- ACTIVE DEFECT LIST ---
        self.sidebar.add_child(gui.Label("ACTIVE DEFECTS:"))
        self.defect_list_container = gui.Vert(2, gui.Margins(0, 4, 0, 4))
        
        self.no_defects_label = gui.Label(" No defects detected.")
        self.no_defects_label.text_color = gui.Color(0.6, 0.6, 0.6)
        self.defect_list_container.add_child(self.no_defects_label)
        
        # Pre-allocate a pool of 15 defect row widgets to work around Open3D's lack of remove_child support
        self.defect_rows = []
        self.defect_buttons = []
        self.delete_buttons = []
        
        for i in range(15):
            row = gui.Horiz(4, gui.Margins(0, 0, 0, 0))
            btn_select = gui.Button("Defect")
            btn_del = gui.Button("X")
            row.add_child(btn_select)
            row.add_child(btn_del)
            row.visible = False
            
            self.defect_list_container.add_child(row)
            self.defect_rows.append(row)
            self.defect_buttons.append(btn_select)
            self.delete_buttons.append(btn_del)
            
        self.sidebar.add_child(self.defect_list_container)
        self._update_defect_list_ui()
        
        self.sidebar.add_child(gui.Label("------------------------------------------------"))
        
        # --- INJECT DEFECT SECTION ---
        self.sidebar.add_child(gui.Label("DEFECT INJECTION TOOL:"))
        
        # Type Select
        self.inject_type_combo = gui.Combobox()
        self.inject_type_combo.add_item("Dent")
        self.inject_type_combo.add_item("Scratch")
        self.sidebar.add_child(self.inject_type_combo)
        
        # Angle Input
        self.sidebar.add_child(gui.Label("Angle (Degrees 0-360):"))
        self.inject_angle_slider = gui.Slider(gui.Slider.INT)
        self.inject_angle_slider.set_limits(0, 359)
        self.inject_angle_slider.double_value = 120.0
        self.sidebar.add_child(self.inject_angle_slider)
        
        # Height Input
        self.sidebar.add_child(gui.Label("Height (Z in meters):"))
        self.inject_height_slider = gui.Slider(gui.Slider.DOUBLE)
        h2 = CAN_HEIGHT / 2.0
        self.inject_height_slider.set_limits(-h2 + 0.005, h2 - 0.005)
        self.inject_height_slider.double_value = 0.030
        self.sidebar.add_child(self.inject_height_slider)
        
        # Confidence Input
        self.sidebar.add_child(gui.Label("Confidence (0.0 - 1.0):"))
        self.inject_conf_slider = gui.Slider(gui.Slider.DOUBLE)
        self.inject_conf_slider.set_limits(0.0, 1.0)
        self.inject_conf_slider.double_value = 0.95
        self.sidebar.add_child(self.inject_conf_slider)
        
        # Size Input
        self.sidebar.add_child(gui.Label("Defect Size / Radius (meters):"))
        self.inject_size_slider = gui.Slider(gui.Slider.DOUBLE)
        self.inject_size_slider.set_limits(0.001, 0.010)
        self.inject_size_slider.double_value = 0.003
        self.sidebar.add_child(self.inject_size_slider)
        
        # Submit Button
        btn_inject = gui.Button("Inject Defect")
        btn_inject.set_on_clicked(self._on_inject_clicked)
        self.sidebar.add_child(btn_inject)
        
        self.sidebar.add_child(gui.Label("------------------------------------------------"))
        
        # --- VIEW PRESETS ---
        self.sidebar.add_child(gui.Label("CAMERA CONTROLS:"))
        camera_grid = gui.Vert(4, gui.Margins(0, 0, 0, 0))
        
        row1 = gui.Horiz(4, gui.Margins(0, 0, 0, 0))
        btn_front = gui.Button("Front")
        btn_front.set_on_clicked(lambda: self._set_camera_preset("Front"))
        btn_back = gui.Button("Back")
        btn_back.set_on_clicked(lambda: self._set_camera_preset("Back"))
        row1.add_child(btn_front)
        row1.add_child(btn_back)
        camera_grid.add_child(row1)
        
        row2 = gui.Horiz(4, gui.Margins(0, 0, 0, 0))
        btn_left = gui.Button("Left")
        btn_left.set_on_clicked(lambda: self._set_camera_preset("Left"))
        btn_right = gui.Button("Right")
        btn_right.set_on_clicked(lambda: self._set_camera_preset("Right"))
        row2.add_child(btn_left)
        row2.add_child(btn_right)
        camera_grid.add_child(row2)
        
        row3 = gui.Horiz(4, gui.Margins(0, 0, 0, 0))
        btn_top = gui.Button("Top")
        btn_top.set_on_clicked(lambda: self._set_camera_preset("Top"))
        btn_bottom = gui.Button("Bottom")
        btn_bottom.set_on_clicked(lambda: self._set_camera_preset("Bottom"))
        row3.add_child(btn_top)
        row3.add_child(btn_bottom)
        camera_grid.add_child(row3)
        
        self.sidebar.add_child(camera_grid)
        
        # Toggle camera rig visualizer
        btn_toggle_rig = gui.Button("Toggle Camera Rig Frustums")
        btn_toggle_rig.set_on_clicked(self._on_toggle_rig_clicked)
        self.sidebar.add_child(btn_toggle_rig)
        
        self.sidebar.add_child(gui.Label("------------------------------------------------"))
        
        # --- REPORT GENERATOR ---
        btn_report = gui.Button("Save Inspection Report")
        btn_report.set_on_clicked(self._on_save_report_clicked)
        self.sidebar.add_child(btn_report)

    def _on_layout(self, layout_context):
        """Layout size and placement calculations."""
        r = self.window.content_rect
        sidebar_width = 330
        self.scene_widget.frame = gui.Rect(r.x, r.y, r.width - sidebar_width, r.height)
        self.sidebar.frame = gui.Rect(r.x + r.width - sidebar_width, r.y, sidebar_width, r.height)

    def add_marker(self, angle: float, height: float, color: str = "red", radius: float = 0.003, confidence: float = 0.95, marker_type: str = "dent",
                   diameter_mm=None, depth_mm=None, length_mm=None, width_mm=None, orientation_deg=None) -> str:
        """
        Public API for adding a marker programmatically.
        Paints surface patches directly on the can mesh (no floating geometries).
        Dents physically deform the can mesh; scratches paint an elongated path.
        """
        color_rgb = (0.9, 0.05, 0.05)
        if color == "blue":
            color_rgb = (0.05, 0.1, 0.9)
        elif color == "green":
            color_rgb = (0.05, 0.9, 0.1)
        elif color == "yellow":
            color_rgb = (0.9, 0.9, 0.05)
            
        self.defect_counter += 1
        defect_id = f"DEFECT_{self.defect_counter:03d}"
        
        label = f"{marker_type.capitalize()} {defect_id}"
        marker = DefectMarker(
            id=defect_id,
            type=marker_type.lower(),
            angle=angle,
            height=height,
            color=color_rgb,
            radius=radius,
            confidence=confidence,
            label=label,
            description=f"{marker_type.capitalize()} at A={angle}°, H={height:.3f}m"
        )
        
        self.active_defects[defect_id] = marker
        
        # 1. If it's a dent, physically deform the can mesh and paint it red!
        if marker.type == "dent":
            d_mm = diameter_mm if diameter_mm is not None else (radius * 2000.0)
            dp_mm = depth_mm if depth_mm is not None else (radius * 500.0)
            
            deform_mesh_for_dent(
                mesh=self.can_body_mesh,
                mapper=self.mapper,
                dent_angle=angle,
                dent_height=height,
                dent_radius=d_mm / 1000.0,
                dent_depth=dp_mm / 1000.0
            )
            self._refresh_can_mesh()
            
        # 2. If it's a scratch, paint the surface blue!
        elif marker.type == "scratch":
            l_mm = length_mm if length_mm is not None else (radius * 4000.0)
            w_mm = width_mm if width_mm is not None else (radius * 250.0)
            o_deg = orientation_deg if orientation_deg is not None else 45.0
            
            paint_scratch_on_mesh(
                mesh=self.can_body_mesh,
                mapper=self.mapper,
                scratch_angle=angle,
                scratch_height=height,
                length_mm=l_mm,
                width_mm=w_mm,
                orientation_deg=o_deg,
                color=color_rgb
            )
            self._refresh_can_mesh()
            
        # 3. Apply Heat Map overlay
        self._recompute_heatmap()
        
        # Update UI sidebar
        self._update_defect_list_ui()
        self._evaluate_can_status()
        
        return defect_id

    def _recompute_heatmap(self):
        """Recalculates can body vertex colors based on active defect locations."""
        hotspots = []
        for marker in self.active_defects.values():
            # weight proportional to confidence and size
            intensity = marker.confidence * 0.8
            hotspots.append((marker.angle, marker.height, intensity))
            
        # Apply to active can body mesh
        apply_heatmap_to_mesh(self.can_body_mesh, hotspots, self.mapper)
        self._refresh_can_mesh()

    def _update_defect_list_ui(self):
        """Updates the pre-created defect list rows in the sidebar pool."""
        if self.headless:
            return
        defects = list(self.active_defects.items())
        num_defects = len(defects)
        
        # Update visibility of the "No defects" label
        self.no_defects_label.visible = (num_defects == 0)
        
        for i in range(15):
            if i < num_defects:
                d_id, defect = defects[i]
                
                # Update select button text and callback
                self.defect_buttons[i].text = f"[{defect.type.upper()}] {d_id} ({defect.confidence*100:.0f}%)"
                self.defect_buttons[i].set_on_clicked(lambda d=defect: self._on_defect_selected(d))
                
                # Update delete button callback
                self.delete_buttons[i].set_on_clicked(lambda did=d_id: self._on_delete_defect(did))
                
                self.defect_rows[i].visible = True
            else:
                self.defect_rows[i].visible = False
                
        # Force redraw of parent
        self.window.post_redraw()

    def _on_defect_selected(self, defect: DefectMarker):
        """Highlights the defect and focuses camera perpendicularly facing it."""
        # Find 3D location
        pos_3d = self.mapper.surface_to_xyz(defect.angle, defect.height)
        
        # Compute perpendicular normal vector
        theta = np.radians(defect.angle)
        normal = np.array([np.cos(theta), np.sin(theta), 0.0])
        
        # Position camera at distance 0.15 m along normal
        cam_pos = pos_3d + 0.15 * normal
        # Tilt camera slightly up for better dimension view
        cam_pos[2] += 0.02
        
        self.scene_widget.look_at(pos_3d, cam_pos, [0.0, 0.0, 1.0])

    def _on_delete_defect(self, defect_id: str):
        """Removes a defect from the system and resets mesh deforming."""
        if defect_id in self.active_defects:
            del self.active_defects[defect_id]
            
            # Remove geometry
            if self.scene_widget.scene.has_geometry(f"marker_{defect_id}"):
                self.scene_widget.scene.remove_geometry(f"marker_{defect_id}")
                
            # Revert can body mesh to clean model and re-apply remaining deformations
            self.can_body_mesh = generate_can_mesh()  # Reset
            
            # Re-apply remaining deformations
            for d_id, marker in self.active_defects.items():
                if marker.type == "dent":
                    deform_mesh_for_dent(
                        mesh=self.can_body_mesh,
                        mapper=self.mapper,
                        dent_angle=marker.angle,
                        dent_height=marker.height,
                        dent_radius=marker.radius * 2.2,
                        dent_depth=marker.radius * 0.7
                    )
            
            # Recompute heatmap overlays
            self._recompute_heatmap()
            self._update_defect_list_ui()
            self._evaluate_can_status()

    def _evaluate_can_status(self):
        """Decides can quality based on inspection guidelines."""
        # Reject if there are any defects with confidence > 0.8
        has_critical_defect = any(m.confidence > 0.8 for m in self.active_defects.values())
        
        if self.headless:
            status = "REJECTED" if has_critical_defect else "PASS"
            print(f"[InspectionRenderer] HEADLESS Can Status Evaluated: {status}")
            return
            
        if has_critical_defect:
            self.status_badge.text = "STATUS: REJECTED"
            self.status_badge.text_color = gui.Color(0.9, 0.2, 0.2) # red
        else:
            self.status_badge.text = "STATUS: PASS"
            self.status_badge.text_color = gui.Color(0.2, 0.9, 0.2) # green

    def _on_inject_clicked(self):
        """Extracts UI slider inputs and calls add_marker."""
        sel_idx = self.inject_type_combo.selected_index
        marker_type = "dent" if sel_idx == 0 else "scratch"
        
        angle = self.inject_angle_slider.double_value
        height = self.inject_height_slider.double_value
        conf = self.inject_conf_slider.double_value
        size = self.inject_size_slider.double_value
        
        color = "red" if marker_type == "dent" else "blue"
        self.add_marker(
            angle=angle,
            height=height,
            color=color,
            radius=size,
            confidence=conf,
            marker_type=marker_type
        )

    def _set_camera_preset(self, name: str):
        """Snaps the viewport camera to preset locations."""
        # Presets relative to coordinate system (meters)
        h2 = CAN_HEIGHT / 2.0
        
        if name == "Front":
            self.scene_widget.look_at([0, 0, 0], [0, -0.25, 0.0], [0, 0, 1])
        elif name == "Back":
            self.scene_widget.look_at([0, 0, 0], [0, 0.25, 0.0], [0, 0, 1])
        elif name == "Left":
            self.scene_widget.look_at([0, 0, 0], [-0.25, 0, 0.0], [0, 0, 1])
        elif name == "Right":
            self.scene_widget.look_at([0, 0, 0], [0.25, 0, 0.0], [0, 0, 1])
        elif name == "Top":
            self.scene_widget.look_at([0, 0, 0], [0, 0, 0.25], [0, 1, 0])
        elif name == "Bottom":
            self.scene_widget.look_at([0, 0, 0], [0, 0, -0.25], [0, -1, 0])

    def _on_toggle_rig_clicked(self):
        """Displays frustums representing the physical multi-camera inspection system."""
        self.show_camera_rig = not self.show_camera_rig
        
        for cam in self.rig_cameras:
            geom_name = f"frustum_{cam.name}"
            if self.show_camera_rig:
                frustum = cam.generate_frustum_geometry(scale=0.03)
                # Unlit green lines
                self.scene_widget.scene.add_geometry(geom_name, frustum, get_glow_material((0.0, 0.9, 0.1)))
            else:
                if self.scene_widget.scene.has_geometry(geom_name):
                    self.scene_widget.scene.remove_geometry(geom_name)
                    
        self.window.post_redraw()

    def _on_save_report_clicked(self):
        """Generates a formatted markdown file summarizing the inspection results."""
        filename = "inspection_report.md"
        status = "REJECTED" if any(m.confidence > 0.8 for m in self.active_defects.values()) else "PASS"
        
        report = []
        report.append("# Coke Can Surface Inspection Report")
        report.append(f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Inspection Status**: **{status}**")
        report.append(f"**Total Defects Detected**: {len(self.active_defects)}")
        report.append("")
        report.append("## Defect Detail Log")
        report.append("| Defect ID | Type | Angle (°) | Height (z) | Confidence | Status | Description |")
        report.append("| --- | --- | --- | --- | --- | --- | --- |")
        
        for d_id, marker in self.active_defects.items():
            level = "CRITICAL" if marker.confidence > 0.8 else "WARNING"
            report.append(
                f"| {d_id} | {marker.type.upper()} | {marker.angle:.1f} | {marker.height:.4f}m | "
                f"{marker.confidence*100:.1f}% | {level} | {marker.description} |"
            )
            
        report_text = "\n".join(report)
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"Inspection report saved to {filename}")
            
            # Show brief visual confirmation in window title
            self.window.title = f"Coke Can Inspection - Digital Twin (Report Saved!)"
            threading.Timer(2.0, lambda: setattr(self.window, 'title', "Coke Can Inspection - Digital Twin")).start()
        except Exception as e:
            print(f"Error saving inspection report: {e}")

    def _animation_loop(self):
        """Thread function calculating pulsing scale transforms at 60 FPS."""
        fps = 60
        delay = 1.0 / fps
        
        while self.running:
            start_time = time.time()
            self.elapsed_time += delay
            
            # Schedule transform updates on main thread
            self.app.post_to_main_thread(self.window, self._animate_markers)
            
            elapsed = time.time() - start_time
            if elapsed < delay:
                time.sleep(delay - elapsed)

    def _animate_markers(self):
        """Updates the geometry transforms of active markers on the main thread."""
        for d_id, marker in self.active_defects.items():
            if not self.scene_widget.scene.has_geometry(f"marker_{d_id}"):
                continue
                
            scale = marker.get_pulse_scale(self.elapsed_time)
            pos_3d = self.mapper.surface_to_xyz(marker.angle, marker.height)
            
            # Construct 4x4 homogenous translation-scale matrix
            T = np.identity(4)
            T[:3, :3] *= scale
            T[:3, 3] = pos_3d
            
            self.scene_widget.scene.set_geometry_transform(f"marker_{d_id}", T)
            
        self.window.post_redraw()

    def save_screenshot(self, filepath, callback=None):
        """Saves a screenshot of the 3D scene widget to a file."""
        if self.headless:
            print("[InspectionRenderer] Screenshot requested in headless mode. Bypassed.")
            if callback:
                callback()
            return
        def on_image_rendered(image):
            try:
                o3d.io.write_image(filepath, image)
                print(f"[InspectionRenderer] Saved Digital Twin screenshot to {filepath}")
                if callback:
                    callback()
            except Exception as e:
                print(f"Error saving screenshot: {e}")
        self.scene_widget.scene.scene.render_to_image(on_image_rendered)

    def _on_close(self):
        """Cleans up threads when window closes."""
        self.running = False
        return True

    def run(self):
        """Launches the UI application event loop."""
        if self.headless:
            import time
            print("[InspectionRenderer] Main Digital Twin thread running in headless mode.")
            print("[InspectionRenderer] Press 'q' or 'ESC' on the camera feed window to exit.")
            try:
                while self.running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
            return
        self.app.run()
