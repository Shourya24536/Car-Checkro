import os
import sys
import json
import csv
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image
from html_template import HTML_TEMPLATE

class ReportGenerator:
    """
    Generates industrial inspection reports in PDF, JSON, and CSV formats.
    """
    def __init__(self, output_dir=None):
        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        else:
            self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_json(self, summary, scratches, dents, filepath):
        """Generates structured JSON report for databases."""
        data = {
            "inspection_summary": summary,
            "defects": {
                "scratches": scratches,
                "dents": dents
            }
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"[ReportGenerator] Saved JSON report to {filepath}")

    def generate_csv(self, scratches, dents, filepath_prefix):
        """Generates tabular CSV reports for Excel."""
        # 1. Scratches CSV
        scratch_file = f"{filepath_prefix}_scratches.csv"
        with open(scratch_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Scratch_ID", "Length_mm", "Width_mm", "Area_mm2", "Angle_deg", "Confidence", "Camera", "Can_Angle_deg", "Can_Height_m"])
            for s in scratches:
                writer.writerow([
                    s["id"], s["length_mm"], s["width_mm"], s["area_mm2"], s["orientation_deg"],
                    s["confidence"], s["camera_id"], s["angle"], s["height"]
                ])
        print(f"[ReportGenerator] Saved Scratches CSV to {scratch_file}")

        # 2. Dents CSV
        dent_file = f"{filepath_prefix}_dents.csv"
        with open(dent_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Dent_ID", "Diameter_mm", "Depth_mm", "Area_mm2", "Severity", "Confidence", "Camera", "Can_Angle_deg", "Can_Height_m"])
            for d in dents:
                writer.writerow([
                    d["id"], d["diameter_mm"], d["depth_mm"], d["area_mm2"], d["severity"],
                    d["confidence"], d["camera_id"], d["angle"], d["height"]
                ])
        print(f"[ReportGenerator] Saved Dents CSV to {dent_file}")

    def generate_pdf(self, summary, scratches, dents, filepath, html_path, annotated_1=None, annotated_2=None):
        """Generates a premium PDF report using matplotlib."""
        # Close any active plots to prevent memory leaks
        plt.close('all')
        
        # Color palette
        c_red = (0.80, 0.05, 0.10)   # Diet Coke Red
        c_gray = (0.45, 0.45, 0.45)  # Metallic Gray
        c_dark = (0.10, 0.10, 0.12)  # Dark Charcoal
        c_green = (0.1, 0.7, 0.2)    # Pass green
        
        with PdfPages(filepath) as pdf:
            # ----------------------------------------------------
            # PAGE 1: Executive Summary & Digital Twin
            # ----------------------------------------------------
            fig = plt.figure(figsize=(8.27, 11.69), dpi=150) # A4 size
            gs = gridspec.GridSpec(3, 1, height_ratios=[1.5, 4.0, 5.0], figure=fig)
            
            # Subplot 0: Header
            ax_header = fig.add_subplot(gs[0])
            ax_header.axis('off')
            ax_header.fill_between([0, 1], 0, 1, color=c_red, transform=ax_header.transAxes)
            
            # Title
            fig.text(0.5, 0.94, "COKE CAN INSPECTION GATEWAY REPORT", 
                     color='white', fontsize=16, weight='bold', ha='center', va='center')
            fig.text(0.5, 0.90, f"PoC Gateway Gateway ID: {summary.get('inspection_id', 'N/A')}", 
                     color='white', fontsize=10, style='italic', ha='center', va='center')
            
            # Subplot 1: Summary Cards
            ax_summary = fig.add_subplot(gs[1])
            ax_summary.axis('off')
            
            # Drawing border
            rect = plt.Rectangle((0.02, 0.02), 0.96, 0.96, fill=False, edgecolor=c_gray, linewidth=1, transform=ax_summary.transAxes)
            ax_summary.add_patch(rect)
            
            # Metadata layout
            meta_y = 0.8
            fig.text(0.08, meta_y + 0.04, "INSPECTION METADATA", fontsize=11, weight='bold', color=c_dark)
            fig.text(0.08, meta_y - 0.08, f"Date: {summary.get('date')}", fontsize=9, color=c_dark)
            fig.text(0.08, meta_y - 0.18, f"Time: {summary.get('time')}", fontsize=9, color=c_dark)
            fig.text(0.08, meta_y - 0.28, f"Duration: {summary.get('processing_time', 0):.2f} sec", fontsize=9, color=c_dark)
            fig.text(0.08, meta_y - 0.38, f"Cameras: {summary.get('cameras_used', 2)} Active", fontsize=9, color=c_dark)
            
            # Statistics layout
            fig.text(0.40, meta_y + 0.04, "DEFECT STATISTICS", fontsize=11, weight='bold', color=c_dark)
            fig.text(0.40, meta_y - 0.08, f"Total Scratches: {len(scratches)}", fontsize=9, color=c_dark)
            fig.text(0.40, meta_y - 0.18, f"Total Dents: {len(dents)}", fontsize=9, color=c_dark)
            
            avg_conf = 0.0
            if scratches or dents:
                all_confs = [s["confidence"] for s in scratches] + [d["confidence"] for d in dents]
                avg_conf = np.mean(all_confs) * 100.0
            fig.text(0.40, meta_y - 0.28, f"Avg Confidence: {avg_conf:.1f}%", fontsize=9, color=c_dark)
            
            max_severity = "N/A"
            if dents:
                severities = [d["severity"] for d in dents]
                if "Critical" in severities:
                    max_severity = "Critical"
                elif "Major" in severities:
                    max_severity = "Major"
                else:
                    max_severity = "Minor"
            fig.text(0.40, meta_y - 0.38, f"Max Severity: {max_severity}", fontsize=9, color=c_dark)
            
            # Result Card (PASS/FAIL)
            res = summary.get("result", "PASS")
            card_color = c_green if res == "PASS" else c_red
            res_rect = plt.Rectangle((0.68, 0.15), 0.24, 0.70, color=card_color, transform=ax_summary.transAxes)
            ax_summary.add_patch(res_rect)
            
            fig.text(0.80, 0.74, "RESULT", color='white', fontsize=10, weight='bold', ha='center')
            fig.text(0.80, 0.60, res, color='white', fontsize=28, weight='bold', ha='center')
            
            # Recommendation
            recom_text = summary.get("recommendation", "No critical defects detected. Can accepted.")
            # Wrap recommendation text if too long
            if len(recom_text) > 40:
                words = recom_text.split()
                recom_text = ""
                line = ""
                for w in words:
                    if len(line + " " + w) > 35:
                        recom_text += line + "\n"
                        line = w
                    else:
                        line = line + " " + w if line else w
                recom_text += line
                
            fig.text(0.80, 0.40, recom_text, color='white', fontsize=7, ha='center', va='center')
            
            # Subplot 2: Clickable 3D Digital Twin Link Button
            ax_twin = fig.add_subplot(gs[2])
            ax_twin.axis('off')
            ax_twin.set_title("3D DIGITAL TWIN DEFECT MAPPING", fontsize=12, weight='bold', color=c_dark, pad=10)
            
            # Border around twin box
            rect_twin = plt.Rectangle((0.02, 0.02), 0.96, 0.96, fill=False, edgecolor=c_gray, linewidth=0.5, transform=ax_twin.transAxes)
            ax_twin.add_patch(rect_twin)
            
            # Draw interactive link button in the center
            html_url = f"file:///{html_path.replace(chr(92), '/')}"
            btn_rect = plt.Rectangle((0.15, 0.42), 0.70, 0.20, color=c_red, transform=ax_twin.transAxes, url=html_url)
            ax_twin.add_patch(btn_rect)
            
            # Text inside button
            ax_twin.text(0.5, 0.52, "CLICK HERE TO OPEN INTERACTIVE 3D DIGITAL TWIN IN CHROME", 
                         color='white', fontsize=8.5, weight='bold', ha='center', va='center', transform=ax_twin.transAxes, url=html_url)
            
            # Subtitle
            ax_twin.text(0.5, 0.30, "Launches WebGL 3D cylinder. Supports orbit rotation, manual defect injection, and deletion.",
                         color=c_gray, fontsize=7.5, ha='center', va='center', transform=ax_twin.transAxes)
                
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            
            # ----------------------------------------------------
            # PAGE 2: Defect Detail Logs & Crops
            # ----------------------------------------------------
            # Group defects for crops grid (max 4 per page, premium cards format)
            all_defects = []
            for s in scratches:
                all_defects.append({"type": "scratch", "data": s})
            for d in dents:
                all_defects.append({"type": "dent", "data": d})
                
            defect_chunks = [all_defects[i:i + 4] for i in range(0, len(all_defects), 4)]
            
            if not defect_chunks:
                # If no defects, print a page indicating that
                fig = plt.figure(figsize=(8.27, 11.69), dpi=150)
                ax = fig.add_subplot(111)
                ax.axis('off')
                fig.text(0.5, 0.5, "NO DEFECTS DETECTED\n\nThis can passed all quality standards.", 
                         fontsize=14, weight='bold', color=c_green, ha='center', va='center')
                pdf.savefig(fig)
                plt.close(fig)
            else:
                for page_idx, chunk in enumerate(defect_chunks):
                    fig = plt.figure(figsize=(8.27, 11.69), dpi=150)
                    
                    # Page Title
                    fig.text(0.08, 0.95, f"DEFECT DETAIL LOGS (PAGE {page_idx + 1}/{len(defect_chunks)})", 
                             fontsize=13, weight='bold', color=c_red)
                    fig.text(0.08, 0.93, "High-resolution camera crops and spatial surface coordinate mappings.", 
                             fontsize=8, color=c_gray)
                    
                    # Create a 2x2 grid of subplots for defects
                    gs_defects = gridspec.GridSpec(2, 2, top=0.90, bottom=0.05, left=0.08, right=0.92, hspace=0.3, wspace=0.25)
                    
                    for idx, item in enumerate(chunk):
                        d_type = item["type"]
                        d_data = item["data"]
                        
                        ax_card = fig.add_subplot(gs_defects[idx])
                        ax_card.axis('off')
                        
                        # Draw border cards with colored outlines (blue for scratch, red for dent)
                        info_color = (0.05, 0.1, 0.9) if d_type == "scratch" else c_red
                        rect_card = plt.Rectangle((0, 0), 1, 1, fill=True, facecolor=(0.97, 0.97, 0.98), edgecolor=info_color, linewidth=1.5, transform=ax_card.transAxes)
                        ax_card.add_patch(rect_card)
                        
                        # Defect Sub-Grid: Left (Crop Image), Right (Text)
                        defect_gs = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs_defects[idx], wspace=0.15)
                        
                        # Column 0: Image crop
                        ax_crop = fig.add_subplot(defect_gs[0])
                        ax_crop.axis('off')
                        crop_path = d_data.get("crop_path")
                        
                        # Crop image border
                        crop_rect = plt.Rectangle((0.05, 0.05), 0.9, 0.9, fill=False, edgecolor=c_gray, linewidth=0.5, transform=ax_crop.transAxes)
                        ax_crop.add_patch(crop_rect)
                        
                        if crop_path and os.path.exists(crop_path):
                            try:
                                img_crop = Image.open(crop_path)
                                ax_crop.imshow(img_crop)
                            except Exception:
                                ax_crop.text(0.5, 0.5, "Image Error", ha='center', va='center', fontsize=8)
                        else:
                            ax_crop.text(0.5, 0.5, "No Crop Image", ha='center', va='center', fontsize=8)
                            
                        # Column 1: Text info
                        ax_info = fig.add_subplot(defect_gs[1])
                        ax_info.axis('off')
                        
                        txt_x = 0.05
                        txt_y = 0.85
                        dy = 0.095
                        
                        ax_info.text(txt_x, txt_y, f"[{d_type.upper()}] {d_data['id']}", fontsize=9, weight='bold', color=info_color)
                        
                        if d_type == "scratch":
                            ax_info.text(txt_x, txt_y - dy, f"Length: {d_data['length_mm']} mm", fontsize=7.5, weight='bold')
                            ax_info.text(txt_x, txt_y - 2*dy, f"Width: {d_data['width_mm']} mm", fontsize=7.5)
                            ax_info.text(txt_x, txt_y - 3*dy, f"Area: {d_data['area_mm2']} mm²", fontsize=7.5)
                            ax_info.text(txt_x, txt_y - 4*dy, f"Orientation: {d_data.get('orientation_deg', 0.0)}°", fontsize=7.5)
                        else:
                            ax_info.text(txt_x, txt_y - dy, f"Diameter: {d_data['diameter_mm']} mm", fontsize=7.5, weight='bold')
                            ax_info.text(txt_x, txt_y - 2*dy, f"Depth: {d_data['depth_mm']} mm", fontsize=7.5)
                            ax_info.text(txt_x, txt_y - 3*dy, f"Area: {d_data['area_mm2']} mm²", fontsize=7.5)
                            severity_val = d_data.get('severity', 'Minor')
                            ax_info.text(txt_x, txt_y - 4*dy, f"Severity: {severity_val}", fontsize=7.5, weight='bold', color=c_red if severity_val in ["Major", "Critical"] else c_dark)
                            
                        ax_info.text(txt_x, txt_y - 5*dy, f"Confidence: {d_data['confidence']*100:.0f}%", fontsize=7.5)
                        ax_info.text(txt_x, txt_y - 6*dy, f"Camera: {d_data['camera_id']}", fontsize=7.5)
                        ax_info.text(txt_x, txt_y - 7*dy, f"Angle: {d_data['angle']:.1f}°", fontsize=7.5)
                        ax_info.text(txt_x, txt_y - 8*dy, f"Height: {d_data['height']:.3f} m", fontsize=7.5)
                        
                    pdf.savefig(fig)
                    plt.close(fig)

            # ----------------------------------------------------
            # PAGE 3: Annotated Camera Captures
            # ----------------------------------------------------
            if annotated_1 or annotated_2:
                fig = plt.figure(figsize=(8.27, 11.69), dpi=150)
                
                # Page Title
                fig.text(0.08, 0.95, "ANNOTATED CAMERA CAPTURES", 
                         fontsize=13, weight='bold', color=c_dark)
                fig.text(0.08, 0.93, "Synchronized dual-camera views showing localized bounding boxes for all active detections.", 
                         fontsize=8, color=c_gray)
                
                gs_cameras = gridspec.GridSpec(2, 1, top=0.90, bottom=0.05, left=0.08, right=0.92, hspace=0.25)
                
                # Camera 1 view
                ax_cam1 = fig.add_subplot(gs_cameras[0])
                ax_cam1.axis('off')
                ax_cam1.set_title("CAMERA 1 (TOP-RIGHT VIEW) - ANNOTATED FEED", fontsize=10, weight='bold', color=c_dark, pad=5)
                rect_c1 = plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor=c_gray, linewidth=0.5, transform=ax_cam1.transAxes)
                ax_cam1.add_patch(rect_c1)
                
                if annotated_1 and os.path.exists(annotated_1):
                    try:
                        img_c1 = Image.open(annotated_1)
                        ax_cam1.imshow(img_c1)
                    except Exception as e:
                        ax_cam1.text(0.5, 0.5, f"Error loading Camera 1 image: {e}", ha='center', va='center')
                else:
                    ax_cam1.text(0.5, 0.5, "Camera 1 annotated frame not available", ha='center', va='center')
                    
                # Camera 2 view
                ax_cam2 = fig.add_subplot(gs_cameras[1])
                ax_cam2.axis('off')
                ax_cam2.set_title("CAMERA 2 (TOP-LEFT VIEW) - ANNOTATED FEED", fontsize=10, weight='bold', color=c_dark, pad=5)
                rect_c2 = plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor=c_gray, linewidth=0.5, transform=ax_cam2.transAxes)
                ax_cam2.add_patch(rect_c2)
                
                if annotated_2 and os.path.exists(annotated_2):
                    try:
                        img_c2 = Image.open(annotated_2)
                        ax_cam2.imshow(img_c2)
                    except Exception as e:
                        ax_cam2.text(0.5, 0.5, f"Error loading Camera 2 image: {e}", ha='center', va='center')
                else:
                    ax_cam2.text(0.5, 0.5, "Camera 2 annotated frame not available", ha='center', va='center')
                    
                pdf.savefig(fig)
                plt.close(fig)
                    
        print(f"[ReportGenerator] Saved PDF report to {filepath}")

    def generate_html_report(self, summary, scratches, dents, html_path, annotated_1=None, annotated_2=None):
        """Generates a premium, interactive WebGL 3D HTML dashboard."""
        all_defects = []
        for s in scratches:
            s_copy = s.copy()
            s_copy["type"] = "scratch"
            s_copy["height"] = float(s_copy["height"])
            s_copy["angle"] = float(s_copy["angle"])
            all_defects.append(s_copy)
        for d in dents:
            d_copy = d.copy()
            d_copy["type"] = "dent"
            d_copy["height"] = float(d_copy["height"])
            d_copy["angle"] = float(d_copy["angle"])
            all_defects.append(d_copy)

        defects_json_list = json.dumps(all_defects)

        # Generate defect detail cards
        cards = []
        for d in all_defects:
            d_id = d["id"]
            d_type = d["type"]
            crop_path = d.get("crop_path")
            rel_crop = f"../crops/{os.path.basename(crop_path)}" if crop_path else ""
            
            img_html = f'<img src="{rel_crop}" alt="Defect {d_id}">' if (crop_path and os.path.exists(crop_path)) else '<div class="no-image-label">No Crop Image Available</div>'
            
            details = ""
            if d_type == "dent":
                details = f"""
                <div class="details-item"><span class="details-label">Diameter</span><span class="details-value">{d.get('diameter_mm', 0.0)} mm</span></div>
                <div class="details-item"><span class="details-label">Depth</span><span class="details-value">{d.get('depth_mm', 0.0)} mm</span></div>
                <div class="details-item"><span class="details-label">Area</span><span class="details-value">{d.get('area_mm2', 0.0)} mm²</span></div>
                <div class="details-item"><span class="details-label">Severity</span><span class="details-value">{d.get('severity', 'Minor')}</span></div>
                """
            else:
                details = f"""
                <div class="details-item"><span class="details-label">Length</span><span class="details-value">{d.get('length_mm', 0.0)} mm</span></div>
                <div class="details-item"><span class="details-label">Width</span><span class="details-value">{d.get('width_mm', 0.0)} mm</span></div>
                <div class="details-item"><span class="details-label">Area</span><span class="details-value">{d.get('area_mm2', 0.0)} mm²</span></div>
                """
                
            details += f"""
            <div class="details-item"><span class="details-label">Confidence</span><span class="details-value">{int(d.get('confidence', 0.0)*100)}%</span></div>
            <div class="details-item"><span class="details-label">Angle</span><span class="details-value">{d.get('angle', 0.0):.1f}°</span></div>
            <div class="details-item"><span class="details-label">Height</span><span class="details-value">{d.get('height', 0.0):.3f} m</span></div>
            <div class="details-item"><span class="details-label">Camera</span><span class="details-value">{d.get('camera_id', 'N/A')}</span></div>
            """
            view_3d_btn = f"""<button class="tab-btn" style="margin-top: 10px; grid-column: span 2; font-size: 11px; padding: 6px;" onclick="switchTab('tab-twin'); focusOnDefectById('{d_id}')">View in 3D Twin</button>"""
            
            card = f"""
            <div class="defect-card {d_type}" id="card-{d_id}">
                <div class="defect-image-area">
                    {img_html}
                </div>
                <div class="defect-info-area">
                    <div class="defect-info-title {d_type}">
                        <span>[{d_type.upper()}] {d_id}</span>
                        <span class="defect-badge {d_type}">{d_type.upper()}</span>
                    </div>
                    <div class="details-list">
                        {details}
                        {view_3d_btn}
                    </div>
                </div>
            </div>
            """
            cards.append(card)

        defect_details_cards = "\\n".join(cards) if cards else '<div class="no-defects">No defects detected during inspection.</div>'

        # Annotated frames feeds
        c1_content = f'<img src="../inspections/{os.path.basename(annotated_1)}" alt="Camera 1 View">' if annotated_1 and os.path.exists(annotated_1) else '<div class="no-feed-msg">Camera 1 annotated frame not available.</div>'
        c2_content = f'<img src="../inspections/{os.path.basename(annotated_2)}" alt="Camera 2 View">' if annotated_2 and os.path.exists(annotated_2) else '<div class="no-feed-msg">Camera 2 annotated frame not available.</div>'

        # Compile template
        html_content = HTML_TEMPLATE
        html_content = html_content.replace("__INSPECTION_ID__", str(summary.get("inspection_id", "N/A")))
        html_content = html_content.replace("__DATE__", str(summary.get("date", "N/A")))
        html_content = html_content.replace("__TIME__", str(summary.get("time", "N/A")))
        html_content = html_content.replace("__RESULT__", str(summary.get("result", "PASS")))
        html_content = html_content.replace("__RESULT_CLASS__", "pass" if summary.get("result", "PASS") == "PASS" else "fail")
        html_content = html_content.replace("__RESULT_BADGE__", "STATUS: PASS" if summary.get("result", "PASS") == "PASS" else "STATUS: REJECTED")
        html_content = html_content.replace("__RECOMMENDATION__", str(summary.get("recommendation", "N/A")))
        html_content = html_content.replace("__NUM_DENTS__", str(len(dents)))
        html_content = html_content.replace("__NUM_SCRATCHES__", str(len(scratches)))
        html_content = html_content.replace("__PROCESSING_TIME__", f"{summary.get('processing_time', 0.0):.2f}")
        html_content = html_content.replace("__DEFECTS_JSON_LIST__", defects_json_list)
        html_content = html_content.replace("__DEFECT_DETAILS_CARDS__", defect_details_cards)
        html_content = html_content.replace("__CAMERA_1_FEED_CONTENT__", c1_content)
        html_content = html_content.replace("__CAMERA_2_FEED_CONTENT__", c2_content)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[ReportGenerator] Saved Interactive 3D HTML Dashboard to {html_path}")

    def generate_all(self, summary, scratches, dents, twin_image_path, prefix, annotated_1=None, annotated_2=None):
        """Generates the PDF report and the supporting HTML 3D Twin."""
        pdf_path = f"{prefix}_report.pdf"
        html_path = f"{prefix}_report.html"
        
        # 1. Generate HTML 3D Twin report first (so PDF can embed the hyperlink)
        self.generate_html_report(summary, scratches, dents, html_path, annotated_1=annotated_1, annotated_2=annotated_2)
        
        # 2. Generate PDF report with link to HTML
        self.generate_pdf(summary, scratches, dents, pdf_path, html_path, annotated_1=annotated_1, annotated_2=annotated_2)
        
        return pdf_path
