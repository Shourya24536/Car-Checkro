from .mapper import CanSurfaceMapper
from .renderer import InspectionRenderer


class DigitalTwin:

    def __init__(self):
        self.mapper = CanSurfaceMapper()
        self.renderer = InspectionRenderer(self.mapper)

    def add_scratch(self, angle, height, confidence=0.95, length_mm=None, width_mm=None, orientation_deg=None):
        self.renderer.add_marker(
            angle=angle,
            height=height,
            color="blue",
            radius=0.003,
            confidence=confidence,
            marker_type="scratch",
            length_mm=length_mm,
            width_mm=width_mm,
            orientation_deg=orientation_deg
        )

    def add_dent(self, angle, height, confidence=0.95, diameter_mm=None, depth_mm=None):
        self.renderer.add_marker(
            angle=angle,
            height=height,
            color="red",
            radius=0.004,
            confidence=confidence,
            marker_type="dent",
            diameter_mm=diameter_mm,
            depth_mm=depth_mm
        )

    def start(self):
        self.renderer.run()


def main():
    twin = DigitalTwin()

    

    twin.start()


if __name__ == "__main__":
    main()