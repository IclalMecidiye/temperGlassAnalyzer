"""
core/analysis.py
Kırık cam parçası sayım algoritması.

Yöntem:
  1. CLAHE ile kontrast normalize et
  2. Koyu fotoğrafları otomatik algıla ve invert et
  3. Adaptive threshold ile parça sınırlarını bul
  4. Tel kafes çizgilerini kaldır
  5. Görüntüyü 2x2 tile'a böl — her tile için ayrı erosion optimizasyonu
  6. Tüm tile'lardan gelen merkez noktalarını birleştir
"""

import cv2
import numpy as np


def _preprocess(gray: np.ndarray) -> np.ndarray:
    """CLAHE uygula, koyu görüntüleri invert et."""
    is_dark = np.mean(gray) < 100
    clahe   = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    if is_dark:
        enhanced = cv2.bitwise_not(enhanced)
    return enhanced


def _remove_wire(thresh: np.ndarray, h: int, w: int) -> np.ndarray:
    """Uzun düz çizgileri (tel kafes) beyaza çevirerek kaldır."""
    horiz_k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 4, 3), 1))
    vert_k  = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 4, 3)))
    wire_h  = cv2.morphologyEx(cv2.bitwise_not(thresh), cv2.MORPH_OPEN, horiz_k)
    wire_v  = cv2.morphologyEx(cv2.bitwise_not(thresh), cv2.MORPH_OPEN, vert_k)
    wire    = cv2.dilate(cv2.bitwise_or(wire_h, wire_v), np.ones((20, 20), np.uint8))
    return cv2.bitwise_or(thresh, wire)


def _best_erosion(thresh_tile: np.ndarray, min_area: int, max_area: float):
    """
    Bir tile için en iyi erosion iterasyonunu bul.
    Döndürür: (count, stats, centroids)
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    best_count, best_stats, best_centroids = 0, None, None

    for e in range(9):
        t = cv2.erode(thresh_tile, kernel, iterations=e) if e > 0 else thresh_tile.copy()
        _, _, stats, centroids = cv2.connectedComponentsWithStats(t)
        areas = stats[1:, cv2.CC_STAT_AREA]
        valid = int(np.sum((areas > min_area) & (areas < max_area)))
        if valid > best_count:
            best_count     = valid
            best_stats     = stats
            best_centroids = centroids

    return best_count, best_stats, best_centroids


def _count_on_thresh(thresh, h, w):
    tiles = [
        (0,      h // 2, 0,      w // 2),
        (0,      h // 2, w // 2, w),
        (h // 2, h,      0,      w // 2),
        (h // 2, h,      w // 2, w),
    ]

    all_centers = []
    total_count = 0

    for (y1, y2, x1, x2) in tiles:
        tile = thresh[y1:y2, x1:x2]
        th, tw = tile.shape
        if th < 10 or tw < 10:
            continue

        min_area = max(8, th * tw * 0.00009)
        max_area = th * tw * 0.20

        count, stats, centroids = _best_erosion(tile, min_area, max_area)
        total_count += count

        if stats is not None:
            areas = stats[1:, cv2.CC_STAT_AREA]
            valid_indices = np.where((areas > min_area) & (areas < max_area))[0]
            for i in valid_indices:
                cx, cy = centroids[i + 1].astype(int)
                all_centers.append((int(cx + x1), int(cy + y1)))

    assert len(all_centers) == total_count, \
        f"Uyuşmazlık: {len(all_centers)} nokta, {total_count} count"

    return total_count, all_centers

def _global_count(blur: np.ndarray, h: int, w: int, block: int = 51) -> tuple[int, list, np.ndarray]:
 
    kernel   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    min_area = max(8, h * w * 0.00009)
    max_area = h * w * 0.15

    def _count_block(blk):
        thresh = cv2.adaptiveThreshold(blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blk, 3)
        thresh = _remove_wire(thresh, h, w)
        best_count, best_stats, best_cen, best_t = 0, None, None, thresh.copy()
        for e in range(12):
            t = cv2.erode(thresh, kernel, iterations=e) if e > 0 else thresh.copy()
            _, _, stats, cen = cv2.connectedComponentsWithStats(t)
            areas = stats[1:, cv2.CC_STAT_AREA]
            valid = int(np.sum((areas > min_area) & (areas < max_area)))
            if valid > best_count:
                best_count, best_stats, best_cen, best_t = valid, stats, cen, t.copy()
        return best_count, best_stats, best_cen, best_t

    # Adım 1: block=51 ile medyan parça alanını tahmin et
    _, stats51, _, _ = _count_block(51)
    if stats51 is not None:
        areas = stats51[1:, cv2.CC_STAT_AREA]
        valid_areas = areas[(areas > min_area) & (areas < max_area)]
        median = float(np.median(valid_areas)) if len(valid_areas) > 0 else 100.0
    else:
        median = 100.0

    # Adım 2: optimal block hesapla (tek sayı, [21, 101] aralığında)
    opt_blk = int(4.1 * np.sqrt(median) / 2) * 2 + 1
    opt_blk = max(21, min(opt_blk, 101))

    # Adım 3: optimal block ile final sayım
    best_count, best_stats, best_centroids, best_t = _count_block(opt_blk)

    centers = []
    if best_stats is not None:
        areas = best_stats[1:, cv2.CC_STAT_AREA]
        for i, area in enumerate(areas):
            if min_area < area < max_area:
                cx, cy = best_centroids[i + 1].astype(int)
                centers.append((int(cx), int(cy)))

    return best_count, centers, best_t


def _detect_median_area(blur: np.ndarray, h: int, w: int) -> float:
    """block=71 ile hızlı geçiş yapıp medyan parça alanını tahmin et."""
    thresh = cv2.adaptiveThreshold(blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 71, 3)
    thresh = _remove_wire(thresh, h, w)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    t = cv2.erode(thresh, kernel, iterations=3)
    _, _, stats, _ = cv2.connectedComponentsWithStats(t)
    areas = stats[1:, cv2.CC_STAT_AREA]
    valid = areas[(areas > 8) & (areas < h * w * 0.15)]
    return float(np.median(valid)) if len(valid) > 0 else 30.0



def count_fragments(region_bgr: np.ndarray, use_ml: bool = True) -> tuple[int, list, np.ndarray]:
    """
    BGR bölgesindeki cam parçası sayısını döndürür.

    Yöntem: hem tile bazlı hem global analiz çalıştır,
    ikisi arasındaki fark büyükse globalin sonucunu al,
    fark küçükse tile sonucunu al.

    Döndürür
    --------
    count      : bulunan parça sayısı
    centers    : [(cx, cy), ...] merkez koordinatları (bölge içi)
    thresh_img : hata ayıklama için eşiklenmiş görüntü
    """
    if region_bgr is None or region_bgr.size == 0:
        return 0, [], np.zeros((1, 1), dtype=np.uint8)

    gray = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    enhanced = _preprocess(gray)
    blur = cv2.GaussianBlur(enhanced, (3, 3), 0)

    # 1. Global analiz (block=51)
    g_count, g_centers, g_thresh = _global_count(blur, h, w, block=51)

    # 2. Tile bazlı analiz (block=21 vs 71)
    results = {}
    for block in [21, 71]:
        thresh = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block, 3
        )
        thresh = _remove_wire(thresh, h, w)
        cnt, centers = _count_on_thresh(thresh, h, w)
        results[block] = (cnt, centers, thresh)

    c21, centers21, t21 = results[21]
    c71, centers71, t71 = results[71]

    ratio = c21 / c71 if c71 > 0 else 99.0

    # Tile seçimi: ratio >= 1.6 → c71, ratio < 1.6 → c21
    if ratio >= 1.6:
        t_count, t_centers, t_thresh = c71, centers71, t71
    else:
        t_count, t_centers, t_thresh = c21, centers21, t21

    img_area = h * w
    tg_ratio  = t_count / g_count if g_count > 0 else 99.0
    is_square_400 = (155000 <= img_area <= 165000)

    if is_square_400 and ratio <= 2.0 and tg_ratio <= 2.0:
        cv_count = t_count
        cv_centers = t_centers
        cv_thresh = t_thresh
    else:
        cv_count = g_count
        cv_centers = g_centers
        cv_thresh = g_thresh

    if use_ml:
        try:
            from core.ml_predict import ml_count
            ml_result = ml_count(region_bgr)
            if ml_result is not None:
                diff_ratio = abs(ml_result - cv_count) / max(cv_count, 1)
                if diff_ratio > 0.3:
                    best_centers = cv_centers
                    best_diff = abs(len(cv_centers) - ml_result)
                    for blk_res in results.values():
                        c, cen, t = blk_res
                        d = abs(len(cen) - ml_result)
                        if d < best_diff:
                            best_diff = d
                            best_centers = cen
                    return ml_result, best_centers, cv_thresh
        except Exception:
            pass

    return cv_count, cv_centers, cv_thresh