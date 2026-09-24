from __future__ import annotations

import cv2
import numpy as np

# Canonical response-grid geometry for the ENEM PARA TODOS / PUC Goiás
# 45-question card. We deliberately warp only the response grid, not the
# whole sheet, so header symbols and the "COMO PREENCHER" examples cannot
# be interpreted as answers.
GRID_W = 900
GRID_H = 760
BLOCK_X = np.array([
    [120, 159, 198, 236, 274],
    [421, 460, 499, 537, 574],
    [724, 763, 801, 838, 877],
], dtype=np.float32)
Y_CENTERS = np.linspace(70, 731, 15, dtype=np.float32)
LETTERS = "ABCDE"


class ScanError(Exception):
    pass


def _order_points(points: np.ndarray) -> np.ndarray:
    points = points.astype(np.float32)
    s = points.sum(axis=1)
    d = np.diff(points, axis=1).reshape(-1)
    return np.array([
        points[np.argmin(s)],      # TL
        points[np.argmin(d)],      # TR
        points[np.argmax(s)],      # BR
        points[np.argmax(d)],      # BL
    ], dtype=np.float32)


def _response_block_candidates(image: np.ndarray) -> list[np.ndarray]:
    """Find the three printed response rectangles.

    These rectangles are a much stronger and safer reference than arbitrary
    circles: each contains exactly 15 questions and five answer columns.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edge_maps = [
        cv2.Canny(blurred, 50, 140),
        cv2.Canny(blurred, 80, 180),
    ]

    h, w = gray.shape
    raw: list[tuple[float, np.ndarray]] = []
    for edges in edge_maps:
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if not (0.035 * h * w < area < 0.22 * h * w):
                continue
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.025 * peri, True)
            if len(approx) != 4:
                continue
            pts = _order_points(approx.reshape(4, 2))
            width = (np.linalg.norm(pts[1] - pts[0]) + np.linalg.norm(pts[2] - pts[3])) / 2
            height = (np.linalg.norm(pts[3] - pts[0]) + np.linalg.norm(pts[2] - pts[1])) / 2
            if height < 1:
                continue
            ratio = width / height
            cy = float(np.mean(pts[:, 1]))
            if not (0.28 < ratio < 0.50):
                continue
            if not (0.25 * h < cy < 0.95 * h):
                continue
            raw.append((area, pts))

    # Remove duplicate contours representing the same printed rectangle.
    raw.sort(key=lambda x: x[0], reverse=True)
    chosen: list[np.ndarray] = []
    for area, pts in raw:
        cx = float(np.mean(pts[:, 0]))
        cy = float(np.mean(pts[:, 1]))
        if any(abs(cx - float(np.mean(q[:, 0]))) < 45 and abs(cy - float(np.mean(q[:, 1]))) < 45 for q in chosen):
            continue
        chosen.append(pts)
        if len(chosen) >= 3:
            break

    # We want exactly three blocks, ordered left-to-right.
    if len(chosen) == 3:
        chosen.sort(key=lambda p: float(np.mean(p[:, 0])))
        return chosen
    return []


def _warp_response_grid(image: np.ndarray) -> tuple[np.ndarray, dict]:
    blocks = _response_block_candidates(image)
    if len(blocks) != 3:
        raise ScanError(
            "Não consegui localizar os três blocos de respostas (01–15, 16–30 e 31–45). "
            "Fotografe a folha inteira, deixando o cartão bem visível e com boa luz."
        )

    left, middle, right = blocks
    # Outer quadrilateral of the response area. This ignores everything above
    # the answer grid, including the instructional bubbles.
    src = np.array([
        left[0],       # left TL
        right[1],      # right TR
        right[2],      # right BR
        left[3],       # left BL
    ], dtype=np.float32)
    dst = np.array([
        [0, 0],
        [GRID_W - 1, 0],
        [GRID_W - 1, GRID_H - 1],
        [0, GRID_H - 1],
    ], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(image, matrix, (GRID_W, GRID_H), flags=cv2.INTER_CUBIC)

    return warped, {
        "response_grid": True,
        "blocks_found": 3,
        "grid_size": [GRID_W, GRID_H],
    }


def _bubble_score(gray: np.ndarray, hsv: np.ndarray, x: float, y: float, radius: int = 8) -> float:
    h, w = gray.shape
    x = float(np.clip(x, radius + 1, w - radius - 2))
    y = float(np.clip(y, radius + 1, h - radius - 2))
    yy, xx = np.ogrid[:h, :w]
    distance2 = (xx - x) ** 2 + (yy - y) ** 2
    inside = distance2 <= radius * radius
    background = (distance2 <= (2.7 * radius) ** 2) & (distance2 >= (1.65 * radius) ** 2)

    center_gray = float(np.median(gray[inside]))
    local_gray = float(np.median(gray[background]))
    center_sat = float(np.median(hsv[:, :, 1][inside]))

    darkness = max(0.0, (local_gray - center_gray) / 255.0)
    color = 0.18 * (center_sat / 255.0)
    return darkness + color


def _classify(row_scores: np.ndarray) -> tuple[str, str | None]:
    order = np.argsort(row_scores)[::-1]
    best_idx = int(order[0])
    second_idx = int(order[1])
    best = float(row_scores[best_idx])
    second = float(row_scores[second_idx])

    # Empty circles normally score near zero; a filled circle is substantially
    # darker. The absolute floor protects against table lines and shadows.
    marked = best >= 0.18
    second_marked = second >= 0.18 and second >= best * 0.55

    if not marked:
        return "BLANK", None
    if second_marked:
        return "MULT", None
    return "OK", LETTERS[best_idx]


def scan_card(image_bytes: bytes) -> dict:
    raw = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ScanError("Imagem inválida.")

    if min(image.shape[:2]) < 650:
        raise ScanError("A foto está com resolução muito baixa. Tire outra foto mais próxima.")

    warped, geometry = _warp_response_grid(image)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)

    questions = []
    for q_index in range(45):
        block = q_index // 15
        row = q_index % 15
        row_scores = np.array([
            _bubble_score(gray, hsv, float(BLOCK_X[block][option]), float(Y_CENTERS[row]))
            for option in range(5)
        ], dtype=np.float32)
        status, answer = _classify(row_scores)
        questions.append({
            "number": q_index + 1,
            "status": status,
            "answer": answer,
            "scores": [round(float(v), 3) for v in row_scores],
        })

    return {
        "questions": questions,
        "threshold": 0.18,
        "geometry": geometry,
    }
