"""
Entry point for the Coke Can Surface Inspection System Digital Twin.
Initializes mapping, default defects, and launches the PBR GUI renderer.
"""
import importlib

def main():
    print("Initializing Coke Can Digital Twin Inspection System...")
    
    # Dynamically load the 'digital_twin' package modules using importlib
    try:
        mapper_module = importlib.import_module("digital_twin.mapper")
        renderer_module = importlib.import_module("digital_twin.renderer")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Ensuring parent directory of 'digital_twin' package is in sys.path...")
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        mapper_module = importlib.import_module("digital_twin.mapper")
        renderer_module = importlib.import_module("digital_twin.renderer")
        
    CanSurfaceMapper = mapper_module.CanSurfaceMapper
    InspectionRenderer = renderer_module.InspectionRenderer

    # 1. Instantiate the surface mapper
    mapper = CanSurfaceMapper()
    
    # 2. Instantiate the interactive PBR GUI renderer
    renderer = InspectionRenderer(mapper)
    
    # 3. Inject initial mock defects for system demonstration
    print("Injecting initial mock defects onto the Digital Twin...")
    
    # A standard dent on the upper body
    renderer.add_marker(
        angle=120.0,
        height=0.030,
        color="red",
        radius=0.0035,
        confidence=0.96,
        marker_type="dent"
    )
    
    # A diagonal scratch on the lower body
    renderer.add_marker(
        angle=45.0,
        height=-0.020,
        color="blue",
        radius=0.0025,
        confidence=0.88,
        marker_type="scratch"
    )
    
    # A minor dent near the bottom shoulder
    renderer.add_marker(
        angle=270.0,
        height=-0.045,
        color="red",
        radius=0.0030,
        confidence=0.75,
        marker_type="dent"
    )
    
    print("Defect injection complete.")
    print("Launching rendering window. Rotate, pan, and zoom to inspect...")
    
    # 4. Start the GUI loop
    renderer.run()

if __name__ == "__main__":
    main()

