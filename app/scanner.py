from __future__ import annotations

import cv2
import numpy as np

# EduScanner V8 — cartão-resposta oficial CEPI-JBR / 45 questões
# Layout baseado no novo modelo enviado pela escola em 24/09/2026.
# Importante: o scanner ignora completamente as bolinhas de "COMO PREENCHER"
# e os campos superiores. A leitura acontece somente nas três grades 01-15,
# 16-30 e 31-45.

PAGE_W, PAGE_H = 768, 1024
BLOCK_W, BLOCK_H = 220, 528
LETTERS = "ABCDE"

# Retângulos relativos ao cartão oficial, depois da correção de perspectiva.
# Cada bloco contém 15 questões e 5 alternativas.
BLOCK_RECTS_REL = [
    (0.0321, 0.4469, 0.3389, 0.9867),
    (0.3598, 0.4469, 0.6611, 0.9867),
    (0.6820, 0.4469, 0.9679, 0.9867),
]

# Centros normalizados das cinco bolhas e das 15 linhas.
# Normalização torna a leitura tolerante a pequenas diferenças de impressão.
X_REL = np.array([0.414, 0.545, 0.673, 0.805, 0.941], dtype=np.float32)
Y_REL = np.array([0.081, 0.144, 0.207, 0.270, 0.333, 0.396, 0.458,
                  0.521, 0.584, 0.646, 0.709, 0.772, 0.835, 0.898,
                  0.961], dtype=np.float32)


class ScanError(Exception):
    pass


def _order_points(points: np.ndarray) -> np.ndarray:
    p = points.astype(np.float32)
    s = p.sum(axis=1)
    d = np.diff(p, axis=1).reshape(-1)
    return np.array([
        p[np.argmin(s)], p[np.argmin(d)],
        p[np.argmax(s)], p[np.argmax(d)]
    ], dtype=np.float32)


def _quad_size(quad: np.ndarray) -> tuple[float, float]:
    p = _order_points(quad)
    w = (np.linalg.norm(p[1] - p[0]) + np.linalg.norm(p[2] - p[3])) / 2
    h = (np.linalg.norm(p[3] - p[0]) + np.linalg.norm(p[2] - p[1])) / 2
    return float(w), float(h)


def _find_card_quad(image: np.ndarray) -> np.ndarray | None:
    """Detect the whole A4 card before reading answers.

    This is more robust than trying to locate three internal rectangles in the
    original camera image. Once the page is rectified, the official template
    has a stable geometry regardless of phone model or camera angle.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    maps = [
        cv2.Canny(blur, 30, 110),
        cv2.Canny(blur, 50, 160),
        cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, 41, 9),
    ]

    candidates: list[tuple[float, np.ndarray]] = []
    for edges in maps:
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE,
                                 np.ones((5, 5), np.uint8), iterations=2)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < 0.22 * h * w or area > 0.98 * h * w:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.025 * peri, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            q = _order_points(approx.reshape(4, 2))
            qw, qh = _quad_size(q)
            if qw <= 0 or qh <= 0:
                continue
            ratio = qw / qh
            # A4 portrait ratio, allowing substantial perspective distortion.
            if not 0.55 < ratio < 0.92:
                continue
            cx = float(np.mean(q[:, 0]))
            cy = float(np.mean(q[:, 1]))
            if not (0.05 * w < cx < 0.95 * w and 0.05 * h < cy < 0.95 * h):
                continue
            score = area * (1.0 - min(abs(ratio - 0.75) / 0.30, 1.0) * 0.25)
            candidates.append((score, q))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _warp_page(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    dst = np.array([
        [0, 0], [PAGE_W - 1, 0],
        [PAGE_W - 1, PAGE_H - 1], [0, PAGE_H - 1]
    ], dtype=np.float32)
    M = cv2.getPerspectiveTransform(_order_points(quad), dst)
    return cv2.warpPerspective(image, M, (PAGE_W, PAGE_H),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)


def _fallback_page(image: np.ndarray) -> np.ndarray:
    """Fallback for photos where the outer paper contour is not closed."""
    # Keep the same aspect ratio and use the central image. This path is only
    # used when document detection fails; answer-block detection below still
    # validates the actual card geometry.
    h, w = image.shape[:2]
    if w / max(h, 1) > 0.95:
        # Landscape source: crop around the central portrait region.
        nw = int(h * 0.78)
        x0 = max((w - nw) // 2, 0)
        image = image[:, x0:x0 + nw]
    return cv2.resize(image, (PAGE_W, PAGE_H), interpolation=cv2.INTER_AREA)


def _find_answer_blocks(page: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Validate/locate the three answer grids on the official template."""
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    out: list[tuple[int, int, int, int]] = []

    # First try the exact official geometry. This prevents the scanner from
    # accidentally selecting the "COMO PREENCHER" circles.
    for rx1, ry1, rx2, ry2 in BLOCK_RECTS_REL:
        x1, y1 = round(rx1 * (PAGE_W - 1)), round(ry1 * (PAGE_H - 1))
        x2, y2 = round(rx2 * (PAGE_W - 1)), round(ry2 * (PAGE_H - 1))
        crop = gray[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        # The grid has many dark structural lines. Require a meaningful edge
        # density but don't require the marks themselves to be present.
        edges = cv2.Canny(crop, 50, 150)
        density = float(np.mean(edges > 0))
        if density >= 0.012:
            out.append((x1, y1, x2, y2))

    if len(out) == 3:
        return out

    # Fallback: detect internal portrait rectangles after page rectification.
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 150)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), 1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if not 0.04 * PAGE_W * PAGE_H < area < 0.25 * PAGE_W * PAGE_H:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        q = _order_points(approx.reshape(4, 2))
        qw, qh = _quad_size(q)
        if qh <= 0 or not 0.32 < qw / qh < 0.55:
            continue
        x1, y1 = np.min(q, axis=0).astype(int)
        x2, y2 = np.max(q, axis=0).astype(int)
        if y1 < 420 or y2 > 1010:
            continue
        candidates.append((area, (int(x1), int(y1), int(x2), int(y2))))
    candidates.sort(key=lambda z: z[0], reverse=True)
    selected: list[tuple[int, int, int, int]] = []
    for _, rect in candidates:
        x1, y1, x2, y2 = rect
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if any(abs(cx - (a + b) / 2) < 30 and abs(cy - (c + d) / 2) < 30
               for a, c, b, d in selected):
            continue
        selected.append(rect)
        if len(selected) == 3:
            break
    if len(selected) == 3:
        return sorted(selected, key=lambda r: r[0])
    return []


def _normalize_illumination(gray: np.ndarray) -> np.ndarray:
    # CLAHE helps with shadows, while preserving the dark center of filled
    # circles. A mild blur reduces camera noise without erasing the marks.
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)


def _score(gray: np.ndarray, hsv: np.ndarray, x: float, y: float) -> float:
    # Bubble radius in the official A4 template after normalization.
    r = 8.8
    yy, xx = np.ogrid[:gray.shape[0], :gray.shape[1]]
    d2 = (xx - x) ** 2 + (yy - y) ** 2
    inside = d2 <= r * r
    ring = (d2 <= 2.7 * r * r) & (d2 >= 1.55 * r * r)

    cg = float(np.median(gray[inside]))
    rg = float(np.median(gray[ring]))
    cs = float(np.median(hsv[:, :, 1][inside]))
    rs = float(np.median(hsv[:, :, 1][ring]))

    # Compare the center against its own ring rather than against a global
    # threshold. This is much less sensitive to Xiaomi/Redmi exposure changes.
    local_dark = float(np.clip((rg - cg) / 70.0, 0, 1))
    chroma = float(np.clip((cs - rs) / 80.0, 0, 1))
    fill = float(np.mean(gray[inside] < rg - 9))
    return 0.68 * local_dark + 0.20 * chroma + 0.12 * fill


def _classify(scores: np.ndarray) -> tuple[str, str | None, float]:
    order = np.argsort(scores)[::-1]
    best = float(scores[order[0]])
    second = float(scores[order[1]])
    baseline = float(np.median(scores))
    spread = best - baseline

    # A filled answer should be significantly darker than the empty printed
    # circles. The second mark rule deliberately catches double markings.
    marked = best >= 0.17 and spread >= 0.035
    second_marked = second >= 0.17 and (second - baseline) >= 0.030 and second >= best * 0.72

    # Confidence combines absolute mark strength and separation from the next
    # alternative. It is surfaced to the review UI for manual confirmation.
    conf = float(np.clip(0.55 * min(best / 0.38, 1.0) +
                         0.45 * ((best - second + 0.04) / 0.18), 0, 1))
    if not marked:
        return "BLANK", None, conf
    if second_marked:
        return "MULT", None, conf
    return "OK", LETTERS[int(order[0])], conf


def scan_card(image_bytes: bytes) -> dict:
    raw = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ScanError("Imagem inválida.")
    if min(image.shape[:2]) < 650:
        raise ScanError("A foto está com resolução muito baixa. Tire outra foto mais próxima.")

    quad = _find_card_quad(image)
    page = _warp_page(image, quad) if quad is not None else _fallback_page(image)
    blocks = _find_answer_blocks(page)
    if len(blocks) != 3:
        raise ScanError(
            "Não consegui localizar as três grades do novo cartão (01–15, 16–30 e 31–45). "
            "Fotografe a folha inteira, mantendo o cartão plano, inteiro e com boa luz."
        )

    questions = []
    block_debug = []
    for bi, (x1, y1, x2, y2) in enumerate(blocks):
        block = page[y1:y2, x1:x2]
        # Use the actual block dimensions, preserving the official geometry.
        gray_raw = cv2.cvtColor(block, cv2.COLOR_BGR2GRAY)
        gray = _normalize_illumination(gray_raw)
        hsv = cv2.cvtColor(block, cv2.COLOR_BGR2HSV)
        bw = block.shape[1]
        bh = block.shape[0]
        block_debug.append([x1, y1, x2, y2])

        for row, yr in enumerate(Y_REL):
            y = float(yr * (bh - 1))
            scores = np.array([
                _score(gray, hsv, float(xr * (bw - 1)), y)
                for xr in X_REL
            ], dtype=np.float32)
            status, answer, conf = _classify(scores)
            questions.append({
                "number": bi * 15 + row + 1,
                "status": status,
                "answer": answer,
                "confidence": round(conf, 2),
                "scores": [round(float(v), 3) for v in scores],
            })

    low = [
        q["number"] for q in questions
        if q["status"] in ("OK", "MULT") and q["confidence"] < 0.62
    ]
    return {
        "questions": questions,
        "threshold": 0.17,
        "geometry": {
            "method": "official_cepi_jbr_45q_page_rectification",
            "template": "cartao_24_09_2026",
            "blocks_found": 3,
            "page_size": [PAGE_W, PAGE_H],
            "blocks": block_debug,
            "card_detected": quad is not None,
        },
        "low_confidence_questions": low,
    }
