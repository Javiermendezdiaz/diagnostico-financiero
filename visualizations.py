#!/usr/bin/env python3
"""
VISUALIZATIONS — FASE 2 Sprint 3
4 visualizaciones TOP 1% usando ReportLab + Matplotlib.
Radar 5D, Heatmap 500q, Timeline Alineación, Tarjetas Fricción.
"""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
import math

@dataclass
class FrictionDimension:
    """Una de las 5 dimensiones de fricción"""
    name: str
    score: float  # 0-100
    color: str  # hex

class Radar5DVisualization:
    """Mapa radar de las 5 dimensiones de fricción"""

    DIMENSIONS = [
        FrictionDimension("Conciliación", 0, "#FF6B6B"),
        FrictionDimension("Finanzas", 0, "#4ECDC4"),
        FrictionDimension("Robustez", 0, "#45B7D1"),
        FrictionDimension("Patrimonio", 0, "#FFA07A"),
        FrictionDimension("Psicología", 0, "#98D8C8"),
    ]

    def __init__(self, friction_scores: Dict[str, float]):
        """
        friction_scores: {
            "conciliacion": 45,
            "finanzas": 67,
            "robustez": 89,
            "patrimonio": 52,
            "psicologia": 73
        }
        """
        self.scores = friction_scores
        self.radius = 150  # pixels

    def draw_on_canvas(self, c: canvas.Canvas, x: float, y: float) -> None:
        """Dibujar radar centrado en (x, y)"""
        # Dibuja 5 ejes (pentágono)
        angle_step = (2 * math.pi) / 5

        # Dibujar grid de fondo (5 anillos concéntricos)
        for ring in range(1, 6):
            ring_radius = self.radius * (ring / 5)
            points = []
            for i in range(5):
                angle = i * angle_step - math.pi / 2
                px = x + ring_radius * math.cos(angle)
                py = y + ring_radius * math.sin(angle)
                points.append((px, py))
            points.append(points[0])  # Cerrar polígono

            c.setStrokeColor(colors.HexColor("#EEEEEE"))
            c.setLineWidth(0.5)
            for i in range(len(points) - 1):
                c.line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        # Dibujar ejes (rayos)
        c.setStrokeColor(colors.HexColor("#CCCCCC"))
        c.setLineWidth(1)
        for i in range(5):
            angle = i * angle_step - math.pi / 2
            end_x = x + self.radius * math.cos(angle)
            end_y = y + self.radius * math.sin(angle)
            c.line(x, y, end_x, end_y)

        # Dibujar polígono de fricción (fill)
        dimension_names = ["conciliacion", "finanzas", "robustez", "patrimonio", "psicologia"]
        polygon_points = []
        for i, name in enumerate(dimension_names):
            score = self.scores.get(name, 0)
            scaled_radius = self.radius * (score / 100)
            angle = i * angle_step - math.pi / 2
            px = x + scaled_radius * math.cos(angle)
            py = y + scaled_radius * math.sin(angle)
            polygon_points.append((px, py))
        polygon_points.append(polygon_points[0])  # Cerrar

        # Draw filled polygon
        c.setFillColor(colors.HexColor("#FDD73160"))  # Amarillo con transparencia
        c.setStrokeColor(colors.HexColor("#FDD731"))
        c.setLineWidth(2)
        c.saveState()
        # Nota: ReportLab no soporta transparencia real en PDF básico, esto es aproximado
        for i in range(len(polygon_points) - 1):
            c.line(polygon_points[i][0], polygon_points[i][1],
                  polygon_points[i + 1][0], polygon_points[i + 1][1])

        # Etiquetas en los ejes
        for i, (dim, name) in enumerate(zip(self.DIMENSIONS, dimension_names)):
            angle = i * angle_step - math.pi / 2
            label_radius = self.radius + 40
            label_x = x + label_radius * math.cos(angle)
            label_y = y + label_radius * math.sin(angle)
            score = self.scores.get(name, 0)

            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(label_x, label_y, f"{dim.name}")
            c.setFont("Helvetica", 9)
            c.drawCentredString(label_x, label_y - 12, f"{int(score)}%")

        c.restoreState()

    def to_pdf_page(self, filename: str) -> None:
        """Exportar radar a PDF de una página"""
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        # Título
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "Mapa de Fricción — 5 Dimensiones")

        # Radar
        self.draw_on_canvas(c, width / 2, height / 2 - 50)

        c.save()


class HeatmapVisualization:
    """Heatmap de 500 preguntas — dónde está la máxima fricción"""

    def __init__(self, question_scores: Dict[int, float]):
        """question_scores: {q001: 85, q002: 45, ...}"""
        self.scores = question_scores

    def to_pdf_page(self, filename: str) -> None:
        """Exportar heatmap a PDF"""
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "Mapa de Calor — 500 Preguntas")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, "Máxima fricción = Rojo | Mínima = Azul")

        # Crear grid 50x10 (500 preguntas)
        cell_width = (width - 100) / 50
        cell_height = (height - 150) / 10
        min_score = min(self.scores.values()) if self.scores else 0
        max_score = max(self.scores.values()) if self.scores else 100

        for q_num in range(1, 501):
            row = (q_num - 1) // 50
            col = (q_num - 1) % 50

            score = self.scores.get(q_num, 50)
            normalized = (score - min_score) / (max_score - min_score + 0.001)

            # Color: rojo (alto) a azul (bajo)
            red = int(255 * normalized)
            blue = int(255 * (1 - normalized))
            color = colors.HexColor(f"#{red:02x}00{blue:02x}")

            x = 50 + col * cell_width
            y = height - 120 - (row + 1) * cell_height

            c.setFillColor(color)
            c.rect(x, y, cell_width, cell_height, fill=1, stroke=0)

        c.save()


class TimelineVisualization:
    """Timeline de alineación — convergencia de visiones pareja"""

    def __init__(self, alignment_data: List[Dict]):
        """
        alignment_data: [
            {"month": 1, "pareja_a": 45, "pareja_b": 60},
            {"month": 2, "pareja_a": 48, "pareja_b": 58},
            ...
        ]
        """
        self.data = alignment_data

    def to_pdf_page(self, filename: str) -> None:
        """Exportar timeline a PDF"""
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "Timeline de Alineación")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, "Línea Pareja A (negro) vs Pareja B (amarillo)")

        # Ejes
        x_axis_y = height - 200
        x_axis_start = 100
        x_axis_end = width - 100

        c.setLineWidth(2)
        c.line(x_axis_start, x_axis_y, x_axis_end, x_axis_y)
        c.line(x_axis_start, x_axis_y, x_axis_start, x_axis_y + 200)

        # Etiquetas de ejes
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_axis_start - 30, x_axis_y - 30, "0%")
        c.drawCentredString((x_axis_start + x_axis_end) / 2, x_axis_y - 50, "Meses")
        c.drawString(x_axis_start - 50, x_axis_y + 150, "100%")

        # Escala
        x_scale = (x_axis_end - x_axis_start) / len(self.data) if self.data else 0
        y_scale = 200 / 100

        # Dibujar líneas
        if len(self.data) > 1:
            # Pareja A (negro)
            c.setStrokeColor(colors.HexColor("#020203"))
            c.setLineWidth(2)
            for i in range(len(self.data) - 1):
                x1 = x_axis_start + i * x_scale
                y1 = x_axis_y + self.data[i]["pareja_a"] * y_scale
                x2 = x_axis_start + (i + 1) * x_scale
                y2 = x_axis_y + self.data[i + 1]["pareja_a"] * y_scale
                c.line(x1, y1, x2, y2)

            # Pareja B (amarillo)
            c.setStrokeColor(colors.HexColor("#FDD731"))
            for i in range(len(self.data) - 1):
                x1 = x_axis_start + i * x_scale
                y1 = x_axis_y + self.data[i]["pareja_b"] * y_scale
                x2 = x_axis_start + (i + 1) * x_scale
                y2 = x_axis_y + self.data[i + 1]["pareja_b"] * y_scale
                c.line(x1, y1, x2, y2)

        c.save()


class FrictionCardsVisualization:
    """Tarjetas visuales de ficción — storytelling"""

    def __init__(self, friction_cards: List[Dict]):
        """
        friction_cards: [
            {
                "title": "Silencio Financiero",
                "friction_score": 85,
                "description": "No hablan de dinero después del trabajo",
                "color": "#FF6B6B"
            },
            ...
        ]
        """
        self.cards = friction_cards

    def to_pdf_page(self, filename: str) -> None:
        """Exportar tarjetas a PDF"""
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "Tarjetas de Fricción — Diagnóstico Visual")

        cards_per_row = 2
        card_width = (width - 100) / cards_per_row
        card_height = 120

        for i, card in enumerate(self.cards[:6]):  # Max 6 cards (2x3 grid)
            row = i // cards_per_row
            col = i % cards_per_row

            x = 50 + col * card_width
            y = height - 150 - row * (card_height + 20)

            # Fondo de tarjeta
            c.setFillColor(colors.HexColor(card.get("color", "#F0F0F0")))
            c.rect(x, y, card_width - 10, card_height, fill=1, stroke=1)

            # Título
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(colors.HexColor("#020203"))
            c.drawString(x + 10, y + card_height - 20, card["title"])

            # Score
            score = card.get("friction_score", 0)
            c.setFont("Helvetica-Bold", 24)
            c.setFillColor(colors.HexColor("#FDD731"))
            c.drawString(x + card_width - 50, y + card_height - 40, f"{int(score)}%")

            # Descripción
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.HexColor("#666666"))
            c.drawString(x + 10, y + 30, card.get("description", ""))

        c.save()


class VisualizationBundle:
    """Bundle de todas las 4 visualizaciones + métodos de exportación"""

    def __init__(self, friction_analysis: Dict):
        """
        friction_analysis: salida de friction_detection.py con:
        - compatibility_score
        - friction_breakdown (por dimensión)
        - question_scores (por q)
        - alignment_timeline
        - friction_cards
        """
        self.analysis = friction_analysis

    def generate_all_to_folder(self, output_folder: str) -> Dict[str, str]:
        """Generar todas las visualizaciones en un folder. Retornar filenames."""

        # Radar 5D
        radar = Radar5DVisualization(
            self.analysis.get("friction_breakdown", {})
        )
        radar_path = f"{output_folder}/01_radar_5d.pdf"
        radar.to_pdf_page(radar_path)

        # Heatmap
        heatmap = HeatmapVisualization(
            self.analysis.get("question_scores", {})
        )
        heatmap_path = f"{output_folder}/02_heatmap_500q.pdf"
        heatmap.to_pdf_page(heatmap_path)

        # Timeline
        timeline = TimelineVisualization(
            self.analysis.get("alignment_timeline", [])
        )
        timeline_path = f"{output_folder}/03_timeline_alineacion.pdf"
        timeline.to_pdf_page(timeline_path)

        # Cards
        cards = FrictionCardsVisualization(
            self.analysis.get("friction_cards", [])
        )
        cards_path = f"{output_folder}/04_tarjetas_friccion.pdf"
        cards.to_pdf_page(cards_path)

        return {
            "radar": radar_path,
            "heatmap": heatmap_path,
            "timeline": timeline_path,
            "cards": cards_path
        }


if __name__ == "__main__":
    # Test
    test_analysis = {
        "friction_breakdown": {
            "conciliacion": 65,
            "finanzas": 78,
            "robustez": 45,
            "patrimonio": 82,
            "psicologia": 55
        },
        "question_scores": {i: (i % 100) for i in range(1, 501)},
        "alignment_timeline": [
            {"month": m, "pareja_a": 40 + m*2, "pareja_b": 70 - m*1.5}
            for m in range(1, 13)
        ],
        "friction_cards": [
            {"title": "Silencio Financiero", "friction_score": 85, "description": "No hablan", "color": "#FF6B6B"},
            {"title": "Desalineación Inversión", "friction_score": 72, "description": "Visiones opuestas", "color": "#FFA07A"},
        ]
    }

    bundle = VisualizationBundle(test_analysis)
    results = bundle.generate_all_to_folder("/tmp")

    print("✅ Visualizations generated:")
    for name, path in results.items():
        print(f"  - {name}: {path}")
