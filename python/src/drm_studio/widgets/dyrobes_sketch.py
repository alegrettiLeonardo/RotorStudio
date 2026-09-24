from __future__ import annotations

"""DyRoBeS/iRdin-style engineering sketch for RotorStudio.

The drawing is presentation-only. It follows the conventions documented in the
DyRoBeS Rotor manual and already proven useful in the legacy RotorDin frontend:
compact radial scale, stepped shaft geometry, cyan mass/package envelopes, A/B
bearing triangles, red unbalance symbols and green grouped response probes.
"""

from collections import OrderedDict
from math import isfinite
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPen, QPolygonF

from drm_studio.application.session import EntityRef


def _alpha(index: int) -> str:
    value = int(index)
    result = ""
    while value >= 0:
        result = chr(ord("A") + value % 26) + result
        value = value // 26 - 1
    return result


def _project_sketch(project) -> dict[str, Any]:
    sketch = dict(project.metadata.get("sketch") or {})
    if sketch:
        return sketch

    model = project.model
    z_mm = {node.number: node.z_m * 1000.0 for node in model.nodes}
    sections = []
    for index, shaft in enumerate(model.shafts, start=1):
        z1 = z_mm.get(shaft.node1, 0.0)
        z2 = z_mm.get(shaft.node2, z1)
        d0 = getattr(shaft, "outer_diameter_m", getattr(shaft, "outer_diameter_1_m", 0.0)) * 1000.0
        d1 = getattr(shaft, "outer_diameter_m", getattr(shaft, "outer_diameter_2_m", d0 / 1000.0)) * 1000.0
        di0 = getattr(shaft, "inner_diameter_m", getattr(shaft, "inner_diameter_1_m", 0.0)) * 1000.0
        di1 = getattr(shaft, "inner_diameter_m", getattr(shaft, "inner_diameter_2_m", di0 / 1000.0)) * 1000.0
        sections.append(
            {
                "index": index,
                "length_mm": max(0.0, z2 - z1),
                "diameter_mm": d0,
                "final_diameter_mm": d1,
                "inner_diameter_mm": di0,
                "final_inner_diameter_mm": di1,
            }
        )

    masses = []
    for index, disk in enumerate(model.disks, start=1):
        x = z_mm.get(disk.node, 0.0)
        if disk.disk_type in (1, 3):
            length = abs(float(disk.p4)) * 1000.0
            outer = abs(float(disk.p5)) * 1000.0
        else:
            length = 0.0
            outer = 0.0
        masses.append(
            {
                "index": index,
                "xi_mm": x - length / 2.0,
                "length_mm": length,
                "mass_kg": float(disk.p3) if disk.disk_type == 2 else 0.0,
                "outer_diameter_mm": outer,
                "package": False,
                "ump": False,
                "inner_diameter_mm": 0.0,
            }
        )

    bearings = [
        {
            "index": index,
            "position_mm": z_mm.get(bearing.node, 0.0),
            "name": f"Bearing {index}",
            "table": [],
        }
        for index, bearing in enumerate(model.bearings, start=1)
    ]

    unbalance = []
    for index, force in enumerate(model.forces, start=1):
        if force.force_type != 1 or len(force.values) < 3:
            continue
        node = int(round(force.values[0]))
        unbalance.append(
            {
                "index": index,
                "position_mm": z_mm.get(node, 0.0),
                "value": float(force.values[1]),
                "phase_deg": float(force.values[2]),
            }
        )

    length = max(z_mm.values(), default=0.0) - min(z_mm.values(), default=0.0)
    return {
        "style": "dyrobes_reference",
        "shaft_length_mm": length,
        "sections": sections,
        "masses": masses,
        "bearings": bearings,
        "unbalance": unbalance,
        "probes": [],
        "concentrated_masses": [],
        "supports": [],
    }


def _shaft_diameter_at(sketch: dict[str, Any], position_mm: float) -> float:
    cursor = 0.0
    sections = sketch.get("sections") or []
    for section in sections:
        length = float(section.get("length_mm", 0.0))
        end = cursor + length
        if cursor - 1.0e-9 <= position_mm <= end + 1.0e-9:
            d0 = float(section.get("diameter_mm", 0.0))
            d1 = float(section.get("final_diameter_mm", d0) or d0)
            ratio = 0.0 if length <= 0.0 else max(0.0, min(1.0, (position_mm - cursor) / length))
            return d0 + (d1 - d0) * ratio
        cursor = end
    if sections:
        last = sections[-1]
        return float(last.get("final_diameter_mm", last.get("diameter_mm", 0.0)) or 0.0)
    return 0.0


def _visual_half_height(sketch: dict[str, Any], position_mm: float, radial_scale: float) -> float:
    half = max(4.0, _shaft_diameter_at(sketch, position_mm) * radial_scale / 2.0)
    for mass in sketch.get("masses") or []:
        start = float(mass.get("xi_mm", 0.0))
        end = start + float(mass.get("length_mm", 0.0))
        if start - 1.0e-9 <= position_mm <= end + 1.0e-9:
            outer = float(mass.get("outer_diameter_mm", 0.0))
            if outer > 0.0:
                half = max(half, outer * radial_scale / 2.0)
    return half


def _add_text(scene, text: str, x: float, y: float, color: str = "#1f2937", scale: float = 0.85):
    item = scene.addText(str(text))
    item.setDefaultTextColor(QColor(color))
    item.setScale(scale)
    item.setPos(x, y)
    item.setZValue(20)
    return item


def build_dyrobes_scene(
    scene,
    session,
    *,
    show_node_numbers: bool = True,
    show_element_numbers: bool = True,
    show_bearings: bool = True,
) -> dict[EntityRef, Any]:
    project = session.project
    model = project.model
    sketch = _project_sketch(project)
    sections = sketch.get("sections") or []
    if not sections:
        text = scene.addText("No rotor model loaded")
        text.setDefaultTextColor(QColor("#5b6976"))
        scene.setSceneRect(0.0, 0.0, 800.0, 400.0)
        return {}

    shaft_length = float(sketch.get("shaft_length_mm") or sum(float(x.get("length_mm", 0.0)) for x in sections))
    shaft_length = max(shaft_length, 1.0)
    shaft_diameters = [
        max(
            float(section.get("diameter_mm", 0.0)),
            float(section.get("final_diameter_mm", section.get("diameter_mm", 0.0)) or 0.0),
        )
        for section in sections
    ]
    mass_diameters = [float(m.get("outer_diameter_mm", 0.0)) for m in sketch.get("masses") or []]
    max_shaft_d = max(shaft_diameters + [50.0])
    max_visual_d = max(shaft_diameters + mass_diameters + [100.0])

    # Compact radial scale is deliberate: the DyRoBeS sketch prioritizes axial
    # topology while preserving relative diameter changes.
    radial_scale = min(0.72, max(0.30, 330.0 / max_visual_d))
    center_y = 0.0
    y_extent = max(115.0, max_visual_d * radial_scale * 0.80 + 65.0)
    entity_items: dict[EntityRef, Any] = {}

    center_pen = QPen(QColor("#aeb8c2"), 0.9, Qt.DashLine)
    scene.addLine(-30.0, center_y, shaft_length + 30.0, center_y, center_pen)

    # Cyan mass/package bodies are painted first so the shaft remains visible
    # through their center band, matching the legacy RotorDin/DyRoBeS sketch.
    for mass_index, mass in enumerate(sketch.get("masses") or []):
        start = float(mass.get("xi_mm", 0.0))
        length = max(4.0, float(mass.get("length_mm", 0.0)))
        outer = float(mass.get("outer_diameter_mm", 0.0)) or max_shaft_d
        half = max(8.0, outer * radial_scale / 2.0)
        rect = QRectF(start, center_y - half, length, 2.0 * half)
        item = scene.addRect(rect, QPen(QColor("#087f87"), 1.1), QBrush(QColor("#19c9d2")))
        item.setZValue(1)
        item.setData(1, "mass")
        item.setData(2, mass_index)

        if mass.get("package"):
            cx = start + length / 2.0
            scene.addEllipse(
                QRectF(cx - 7.0, center_y - 7.0, 14.0, 14.0),
                QPen(QColor("#111111"), 1.0),
                QBrush(QColor("#ffffff")),
            ).setZValue(11)
            scene.addEllipse(
                QRectF(cx - 2.2, center_y - 2.2, 4.4, 4.4),
                QPen(QColor("#111111"), 0.8),
                QBrush(QColor("#111111")),
            ).setZValue(12)
        _add_text(scene, chr(ord("a") + mass_index) if mass_index < 26 else f"m{mass_index+1}", start + length / 2.0 - 5.0, center_y - half - 26.0, "#075f68")

    gradient = QLinearGradient(0.0, -max_shaft_d * radial_scale / 2.0, 0.0, max_shaft_d * radial_scale / 2.0)
    gradient.setColorAt(0.00, QColor("#f3f4f6"))
    gradient.setColorAt(0.43, QColor("#7d8288"))
    gradient.setColorAt(0.56, QColor("#f8f8f8"))
    gradient.setColorAt(1.00, QColor("#aeb4ba"))

    cursor = 0.0
    station_positions = [0.0]
    for index, section in enumerate(sections):
        length = float(section.get("length_mm", 0.0))
        d0 = float(section.get("diameter_mm", 0.0)) * radial_scale
        d1 = float(section.get("final_diameter_mm", section.get("diameter_mm", 0.0)) or 0.0) * radial_scale
        polygon = QPolygonF(
            [
                QPointF(cursor, center_y - d0 / 2.0),
                QPointF(cursor + length, center_y - d1 / 2.0),
                QPointF(cursor + length, center_y + d1 / 2.0),
                QPointF(cursor, center_y + d0 / 2.0),
            ]
        )
        item = scene.addPolygon(polygon, QPen(QColor("#20252b"), 1.0), QBrush(gradient))
        item.setZValue(4)
        item.setData(1, "shaft")
        if index < len(model.shafts):
            ref = EntityRef("shaft", index)
            item.setData(0, ref)
            entity_items[ref] = item

        di0 = float(section.get("inner_diameter_mm", 0.0)) * radial_scale
        di1 = float(section.get("final_inner_diameter_mm", section.get("inner_diameter_mm", 0.0)) or 0.0) * radial_scale
        if di0 > 0.0 or di1 > 0.0:
            scene.addLine(
                cursor,
                center_y - di0 / 2.0,
                cursor + length,
                center_y - di1 / 2.0,
                QPen(QColor("#59636e"), 0.8, Qt.DashLine),
            ).setZValue(5)
            scene.addLine(
                cursor,
                center_y + di0 / 2.0,
                cursor + length,
                center_y + di1 / 2.0,
                QPen(QColor("#59636e"), 0.8, Qt.DashLine),
            ).setZValue(5)

        if show_element_numbers:
            _add_text(scene, str(index + 1), cursor + length / 2.0 - 4.0, -max_shaft_d * radial_scale / 2.0 - 28.0, "#1f2937", 0.78)
        cursor += length
        station_positions.append(cursor)

    if show_node_numbers:
        for idx, xpos in enumerate(station_positions, start=1):
            dot = scene.addEllipse(
                QRectF(xpos - 2.8, center_y - 2.8, 5.6, 5.6),
                QPen(QColor("#52606d"), 0.8),
                QBrush(QColor("#ffdf4f")),
            )
            dot.setZValue(10)
            dot.setData(1, "station")
            _add_text(scene, str(idx), xpos - 4.0, max_shaft_d * radial_scale / 2.0 + 12.0, "#34495e", 0.66)

    if show_bearings:
        for index, bearing in enumerate(sketch.get("bearings") or []):
            x = float(bearing.get("position_mm", 0.0))
            shaft_half = max(4.0, _shaft_diameter_at(sketch, x) * radial_scale / 2.0)
            apex = center_y + shaft_half + 4.0
            base = apex + 17.0
            poly = QPolygonF([QPointF(x, apex), QPointF(x - 10.0, base), QPointF(x + 10.0, base)])
            item = scene.addPolygon(poly, QPen(QColor("#111111"), 1.25), QBrush(Qt.NoBrush))
            item.setZValue(12)
            item.setData(1, "bearing")
            item.setData(2, index)
            scene.addLine(x - 13.0, base + 2.0, x + 13.0, base + 2.0, QPen(QColor("#111111"), 1.0)).setZValue(12)
            _add_text(scene, _alpha(index), x - 5.0, base + 4.0, "#173a5e", 0.78)

    for index, force in enumerate(sketch.get("unbalance") or [], start=1):
        x = float(force.get("position_mm", 0.0))
        top = center_y - _visual_half_height(sketch, x, radial_scale)
        cy = top - 30.0
        scene.addLine(x, top, x, cy + 9.0, QPen(QColor("#e13d43"), 1.4)).setZValue(13)
        unbalance_item = scene.addEllipse(
            QRectF(x - 8.0, cy - 8.0, 16.0, 16.0),
            QPen(QColor("#e13d43"), 1.4),
            QBrush(Qt.NoBrush),
        )
        unbalance_item.setZValue(13)
        unbalance_item.setData(1, "unbalance")
        unbalance_item.setData(2, index - 1)
        scene.addLine(x - 4.5, cy, x + 4.5, cy, QPen(QColor("#e13d43"), 1.2)).setZValue(14)
        _add_text(scene, f"u{index}", x + 8.0, cy - 10.0, "#c92a2a", 0.72)

    grouped: OrderedDict[float, list[int]] = OrderedDict()
    for probe in sketch.get("probes") or []:
        pos = float(probe.get("position_mm", 0.0))
        grouped.setdefault(round(pos, 8), []).append(int(probe.get("index", len(grouped) + 1)))
    for key, indices in grouped.items():
        x = float(key)
        top = center_y - _visual_half_height(sketch, x, radial_scale)
        junction = top - 22.0
        color = QColor("#2f9e44")
        pen = QPen(color, 1.25)
        probe_item = scene.addLine(x, top, x, junction, pen)
        probe_item.setZValue(13)
        probe_item.setData(1, "probe")
        probe_item.setData(2, tuple(indices))
        if len(indices) >= 2:
            arm_y = junction - 14.0
            scene.addLine(x, junction, x - 13.0, arm_y, pen).setZValue(13)
            scene.addLine(x, junction, x + 13.0, arm_y, pen).setZValue(13)
            ordered = sorted(indices, reverse=True)
            _add_text(scene, f"r{ordered[0]}", x - 27.0, arm_y - 18.0, "#2f9e44", 0.70)
            _add_text(scene, f"r{ordered[1]}", x + 10.0, arm_y - 18.0, "#2f9e44", 0.70)
        else:
            scene.addLine(x - 7.0, junction, x + 7.0, junction, pen).setZValue(13)
            _add_text(scene, f"r{indices[0]}", x - 10.0, junction - 20.0, "#2f9e44", 0.70)

    # Compact axis reference; Z is the rotor spin/axial axis in DyRoBeS.
    x0 = -10.0
    ay = y_extent - 20.0
    scene.addLine(x0, ay, x0 + 55.0, ay, QPen(QColor("#111111"), 1.3)).setZValue(30)
    scene.addLine(x0, ay, x0, ay - 38.0, QPen(QColor("#111111"), 1.3)).setZValue(30)
    _add_text(scene, "Z", x0 + 57.0, ay - 9.0, "#111111", 0.8)
    _add_text(scene, "Y", x0 - 12.0, ay - 54.0, "#111111", 0.8)

    scene.setSceneRect(-45.0, -y_extent, shaft_length + 90.0, 2.0 * y_extent)
    return entity_items


__all__ = ["build_dyrobes_scene"]
