import cv2
import numpy as np
from config import RENK1_CV, RENK2_CV

BOX_COLORS = [RENK1_CV, RENK2_CV]


def draw_boxes(img, boxes):
    for i, b in enumerate(boxes):
        x1, x2 = sorted([b[0], b[2]])
        y1, y2 = sorted([b[1], b[3]])
        renk = BOX_COLORS[i]
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), renk, -1)
        cv2.addWeighted(overlay, 0.12, img, 0.88, 0, img)
        cv2.rectangle(img, (x1, y1), (x2, y2), renk, 3)
        label = f"Bolge {i + 1}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(img, (x1, y1), (x1 + tw + 12, y1 + th + 10), renk, -1)
        cv2.putText(img, label, (x1 + 6, y1 + th + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (10, 10, 10), 2)


def draw_analysis_result(img, results):
    counts = [r[0] for r in results]
    max_c  = max(counts)
    min_c  = min(counts)
    for i, (count, x1, y1, x2, y2, centers) in enumerate(results):
        renk = BOX_COLORS[i]
        if   count == max_c: etiket = f"EN FAZLA: {count}"
        elif count == min_c: etiket = f"EN AZ: {count}"
        else:                etiket = f"Bolge {i + 1}: {count}"
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), renk, -1)
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
        cv2.rectangle(img, (x1, y1), (x2, y2), renk, 3)
        (tw, th), _ = cv2.getTextSize(etiket, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
        ty = max(y1 - 8, th + 6)
        cv2.rectangle(img, (x1, ty - th - 8), (x1 + tw + 12, ty + 4), renk, -1)
        cv2.putText(img, etiket, (x1 + 6, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (10, 10, 10), 2)
        for cx, cy in centers[:count]:
            cv2.circle(img, (x1 + cx, y1 + cy), 3, renk, -1)


def draw_preview_box(img, x1, y1, x2, y2):
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 160, 255), -1)
    cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 160, 255), 2)
    info = f"{abs(x2 - x1)} x {abs(y2 - y1)} px"
    cv2.putText(img, info, (x1 + 4, y2 - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
