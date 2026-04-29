"""
Bounding box içindeki baskın rengi tespit eder.
Güvenlik kamerası senaryosunda araç rengi gibi bilgiler için kullanılır.
"""
import cv2
import numpy as np

# HSV renk aralıkları
_COLOR_RANGES = {
    "kırmızı":  [((0, 100, 100), (10, 255, 255)), ((160, 100, 100), (180, 255, 255))],
    "turuncu":  [((11, 100, 100), (25, 255, 255))],
    "sarı":     [((26, 100, 100), (35, 255, 255))],
    "yeşil":    [((36, 100, 100), (85, 255, 255))],
    "mavi":     [((86, 100, 100), (125, 255, 255))],
    "mor":      [((126, 100, 100), (159, 255, 255))],
    "beyaz":    [((0, 0, 200), (180, 30, 255))],
    "siyah":    [((0, 0, 0), (180, 255, 50))],
    "gri":      [((0, 0, 51), (180, 50, 200))],
}


def dominant_color(image: np.ndarray, bbox: tuple[int, int, int, int]) -> str:
    """
    BGR image ve (x1,y1,x2,y2) bbox alır; baskın renk adını döndürür.
    Bilinmeyen renk için 'belirsiz' döner.
    """
    x1, y1, x2, y2 = bbox
    roi = image[max(0, y1):y2, max(0, x1):x2]
    if roi.size == 0:
        return "belirsiz"

    roi_small = cv2.resize(roi, (64, 64))
    hsv = cv2.cvtColor(roi_small, cv2.COLOR_BGR2HSV)

    scores: dict[str, int] = {}
    for color_name, ranges in _COLOR_RANGES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
        scores[color_name] = int(mask.sum())

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 200 else "belirsiz"
