"""Renk tespiti testleri."""
import numpy as np
import pytest


def test_red_detection():
    from video_analyzer.color_detector import dominant_color
    # Kırmızı piksellerden oluşan 100x100 görüntü (BGR)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = (0, 0, 200)  # BGR kırmızı
    color = dominant_color(img, (0, 0, 100, 100))
    assert color == "kırmızı"


def test_blue_detection():
    from video_analyzer.color_detector import dominant_color
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = (200, 0, 0)  # BGR mavi
    color = dominant_color(img, (0, 0, 100, 100))
    assert color == "mavi"


def test_empty_roi():
    from video_analyzer.color_detector import dominant_color
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Geçersiz bbox (sıfır alanlı)
    color = dominant_color(img, (50, 50, 50, 50))
    assert color == "belirsiz"
