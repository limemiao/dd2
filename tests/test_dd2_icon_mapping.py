"""Regression tests for Dragon's Dogma 2 equipment icon atlas mapping."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from build_dd2_equipment_catalog import atlas_series_for_icon, crop_icon
from PIL import Image


class EquipmentIconMappingTests(unittest.TestCase):
    def test_regular_icon_keeps_its_atlas_series(self) -> None:
        self.assertEqual(atlas_series_for_icon(3062), 3)
        self.assertEqual(atlas_series_for_icon(4016), 4)

    def test_expansion_icon_series_uses_previous_atlas(self) -> None:
        self.assertEqual(atlas_series_for_icon(12040), 11)
        self.assertEqual(atlas_series_for_icon(13002), 12)
        self.assertEqual(atlas_series_for_icon(13084), 12)
        self.assertEqual(atlas_series_for_icon(14000), 13)

    def test_zero_icon_uses_placeholder_instead_of_atlas_cell(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            atlas_dir = root / "atlas"
            atlas_dir.mkdir()
            Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(
                atlas_dir / "tex_ui01c00_00_iam.png"
            )
            output = root / "icon.png"
            availability = crop_icon(
                0, atlas_dir, output, root / "_no_icon.png", force=True
            )
            self.assertEqual(availability, "missing")
            with Image.open(output) as image:
                self.assertEqual(image.size, (234, 234))


if __name__ == "__main__":
    unittest.main()
