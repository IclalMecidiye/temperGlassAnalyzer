"""
core/ml_predict.py  -  ML modeli ile parça sayımı tahmini.
Hem sklearn (GradientBoosting) hem PyTorch modellerini destekler.
"""

import hashlib
import hmac
import logging
import os
import pickle

import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_model.pkl')
MODEL_HASH_PATH = MODEL_PATH + '.sha256'
_cache: dict = {}

# Known SHA-256 hash of the trusted ml_model.pkl shipped with the repo.
_TRUSTED_HASH = "e3bd7796e4eee4ab40f44fa2f8b0c525941a7d6ceaf5c31a277dece5f96a0b42"


def _verify_model_integrity(data: bytes) -> bool:
    """Verify the pickle file has not been tampered with.

    Checks the SHA-256 digest of the raw bytes against the hard-coded
    trusted hash.  Returns True only when the file matches.
    """
    file_hash = hashlib.sha256(data).hexdigest()
    return hmac.compare_digest(file_hash, _TRUSTED_HASH)


def _load():
    if 'data' not in _cache:
        if not os.path.exists(MODEL_PATH):
            return None
        with open(MODEL_PATH, 'rb') as f:
            raw = f.read()
        if not _verify_model_integrity(raw):
            logger.warning(
                "ml_model.pkl integrity check FAILED — the file may have "
                "been tampered with.  Model will NOT be loaded."
            )
            return None
        _cache['data'] = pickle.loads(raw)  # noqa: S301 — verified above
    return _cache['data']


def extract_features(img):
    import cv2
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    enh = clahe.apply(gray)
    if np.mean(gray) < 100:
        enh = cv2.bitwise_not(enh)
    bl = cv2.GaussianBlur(enh, (3, 3), 0)
    feats = [float(np.mean(bl)), float(np.std(bl)), float(np.median(bl)),
             float(h), float(w), float(h * w)]
    edges = cv2.Canny(bl, 50, 150)
    feats.append(float(np.sum(edges > 0) / (h * w)))
    lap = cv2.Laplacian(bl, cv2.CV_64F)
    feats += [float(np.var(lap)), float(np.mean(np.abs(lap)))]
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    blk_counts = []
    for blk in [21, 31, 41, 51, 71, 91]:
        t = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, blk, 3)
        best = 0
        min_a = max(8, h * w * 0.00009)
        max_a = h * w * 0.15
        for e in range(8):
            te = cv2.erode(t, ker, iterations=e) if e > 0 else t.copy()
            _, _, st, _ = cv2.connectedComponentsWithStats(te)
            v = int(np.sum((st[1:, cv2.CC_STAT_AREA] > min_a) &
                           (st[1:, cv2.CC_STAT_AREA] < max_a)))
            if v > best:
                best = v
        blk_counts.append(float(best))
    feats += blk_counts
    feats += [float(max(blk_counts)), float(blk_counts[0] - blk_counts[-1]),
              float(blk_counts[0] / blk_counts[-1]) if blk_counts[-1] > 0 else 1.0]
    t51 = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 51, 3)
    _, _, st51, _ = cv2.connectedComponentsWithStats(t51)
    areas = st51[1:, cv2.CC_STAT_AREA]
    av = areas[areas > 5]
    feats += [float(np.median(av)) if len(av) > 0 else 0.,
              float(np.mean(av))   if len(av) > 0 else 0.,
              float(np.std(av))    if len(av) > 0 else 0.]
    return np.array(feats).reshape(1, -1)


def ml_count(img) -> int | None:
    data = _load()
    if data is None:
        return None
    try:
        feats = extract_features(img)
        scaler = data['scaler']
        feats_scaled = scaler.transform(feats)

        model_type = data.get('model_type', 'sklearn')

        if model_type == 'pytorch':
            import torch
            import torch.nn as nn

            class CountNet(nn.Module):
                def __init__(self, input_dim):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, 256),
                        nn.ReLU(), nn.Dropout(0.3),
                        nn.Linear(256, 128),
                        nn.ReLU(), nn.Dropout(0.2),
                        nn.Linear(128, 64),
                        nn.ReLU(),
                        nn.Linear(64, 1)
                    )
                def forward(self, x):
                    return self.net(x).squeeze()

            if 'nn_model' not in _cache:
                m = CountNet(data['input_dim'])
                m.load_state_dict(data['model_state'])
                m.eval()
                _cache['nn_model'] = m

            with torch.no_grad():
                x = torch.FloatTensor(feats_scaled)
                pred = _cache['nn_model'](x).item()
        else:
            pred = data['model'].predict(feats_scaled)[0]

        return max(1, int(round(pred)))
    except Exception:
        return None
