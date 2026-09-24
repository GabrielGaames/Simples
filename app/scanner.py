from __future__ import annotations

import cv2
import numpy as np

# EduScanner V4 — PUC Goiás / ENEM PARA TODOS 45Q
# Strategy: locate the three printed response rectangles, rectify EACH block
# independently, then sample a fixed 15x5 grid. This avoids using the
# "COMO PREENCHER" bubbles and is much more tolerant of mobile-camera
# perspective, rotation, distance and local shadows.
BLOCK_W, BLOCK_H = 300, 760
X = np.array([120, 159, 198, 236, 274], dtype=np.float32)
Y = np.linspace(70, 731, 15, dtype=np.float32)
LETTERS = "ABCDE"

class ScanError(Exception):
    pass


def _order_points(points: np.ndarray) -> np.ndarray:
    p = points.astype(np.float32)
    s = p.sum(axis=1)
    d = np.diff(p, axis=1).reshape(-1)
    return np.array([p[np.argmin(s)], p[np.argmin(d)], p[np.argmax(s)], p[np.argmax(d)]], dtype=np.float32)


def _find_blocks(image: np.ndarray) -> list[np.ndarray]:
    """Find the three large printed answer rectangles, not answer circles."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    maps = [cv2.Canny(blurred, 35, 120), cv2.Canny(blurred, 60, 170)]
    # Adaptive edges help when one side of a phone photo is shadowed.
    adap = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 31, 7)
    maps.append(adap)
    raw = []
    for edges in maps:
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5,5),np.uint8), iterations=1)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if not (0.025*h*w < area < 0.25*h*w):
                continue
            peri = cv2.arcLength(c, True)
            if peri < 100: continue
            approx = cv2.approxPolyDP(c, 0.02*peri, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            pts = _order_points(approx.reshape(4,2))
            tw=(np.linalg.norm(pts[1]-pts[0])+np.linalg.norm(pts[2]-pts[3]))/2
            th=(np.linalg.norm(pts[3]-pts[0])+np.linalg.norm(pts[2]-pts[1]))/2
            if th <= 0: continue
            ratio=tw/th
            cy=float(np.mean(pts[:,1]))
            # Three blocks are tall portrait rectangles.
            if 0.28 < ratio < 0.58 and 0.22*h < cy < 0.97*h:
                raw.append((area,pts))
    raw.sort(key=lambda x:x[0], reverse=True)
    chosen=[]
    for area,pts in raw:
        cx=float(np.mean(pts[:,0])); cy=float(np.mean(pts[:,1]))
        if any(abs(cx-float(np.mean(q[:,0])))<35 and abs(cy-float(np.mean(q[:,1])))<35 for q in chosen):
            continue
        chosen.append(pts)
        if len(chosen)==3: break
    if len(chosen)==3:
        return sorted(chosen, key=lambda p: float(np.mean(p[:,0])))
    return []


def _warp_block(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    dst=np.array([[0,0],[BLOCK_W-1,0],[BLOCK_W-1,BLOCK_H-1],[0,BLOCK_H-1]],np.float32)
    M=cv2.getPerspectiveTransform(_order_points(quad),dst)
    return cv2.warpPerspective(image,M,(BLOCK_W,BLOCK_H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)


def _score(gray: np.ndarray, hsv: np.ndarray, x: float, y: float) -> float:
    r=9
    yy,xx=np.ogrid[:gray.shape[0],:gray.shape[1]]
    d2=(xx-x)**2+(yy-y)**2
    inside=d2<=r*r
    ring=(d2<=3.0*r*r)&(d2>=1.75*r*r)
    cg=float(np.median(gray[inside])); rg=float(np.median(gray[ring]))
    cs=float(np.median(hsv[:,:,1][inside])); rs=float(np.median(hsv[:,:,1][ring]))
    darkness=float(np.clip((rg-cg)/80.0,0,1))
    chroma=float(np.clip((cs-rs)/90.0,0,1))
    # Ink fills much of the center; printed empty circles mostly leave a white center.
    ring_med=float(np.median(gray[ring]))
    fill=float(np.mean(gray[inside] < ring_med-10))
    return 0.62*darkness + 0.23*chroma + 0.15*fill


def _classify(scores: np.ndarray) -> tuple[str,str|None,float]:
    order=np.argsort(scores)[::-1]
    best=float(scores[order[0]]); second=float(scores[order[1]])
    baseline=float(np.median(scores))
    marked=best >= 0.20 and best-baseline >= 0.045
    second_marked=second >= 0.20 and second-baseline >= 0.045 and second >= best*0.68
    # Confidence is deliberately conservative: close alternatives are flagged.
    conf=float(np.clip((best-second+0.08)*1.8,0,1))
    if not marked: return "BLANK",None,conf
    if second_marked: return "MULT",None,conf
    return "OK",LETTERS[int(order[0])],conf


def scan_card(image_bytes: bytes) -> dict:
    raw=np.frombuffer(image_bytes,dtype=np.uint8)
    image=cv2.imdecode(raw,cv2.IMREAD_COLOR)
    if image is None: raise ScanError("Imagem inválida.")
    if min(image.shape[:2])<650:
        raise ScanError("A foto está com resolução muito baixa. Tire outra foto mais próxima.")

    blocks=_find_blocks(image)
    if len(blocks)!=3:
        raise ScanError("Não consegui localizar os três blocos de respostas (01–15, 16–30 e 31–45). Fotografe a folha inteira, deixando o cartão bem visível e com boa luz.")

    questions=[]
    block_debug=[]
    for bi,quad in enumerate(blocks):
        warped=_warp_block(image,quad)
        gray=cv2.cvtColor(warped,cv2.COLOR_BGR2GRAY)
        gray=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
        hsv=cv2.cvtColor(warped,cv2.COLOR_BGR2HSV)
        block_debug.append(_order_points(quad).round(1).tolist())
        for row,y in enumerate(Y):
            scores=np.array([_score(gray,hsv,float(x),float(y)) for x in X],dtype=np.float32)
            status,answer,conf=_classify(scores)
            questions.append({
                "number":bi*15+row+1,
                "status":status,
                "answer":answer,
                "confidence":round(conf,2),
                "scores":[round(float(v),3) for v in scores],
            })

    low=[q["number"] for q in questions if q["status"]=="OK" and q["confidence"]<0.55]
    return {
        "questions":questions,
        "threshold":0.20,
        "geometry":{"method":"three_independent_response_blocks","blocks_found":3,"block_size":[BLOCK_W,BLOCK_H],"corners":block_debug},
        "low_confidence_questions":low,
    }
