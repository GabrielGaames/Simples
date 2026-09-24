import cv2
import numpy as np
from app.scanner import scan_card


def make_card():
    img = np.full((1024, 768, 3), 245, np.uint8)
    cv2.rectangle(img, (25, 20), (742, 1000), (30,30,30), 3)
    for x1,y1,x2,y2 in [(48,458,268,987),(283,458,499,987),(514,458,719,987)]:
        cv2.rectangle(img,(x1,y1),(x2,y2),(50,50,50),2)
        for row,yr in enumerate(np.array([0.081,0.144,0.207,0.270,0.333,0.396,0.458,0.521,0.584,0.646,0.709,0.772,0.835,0.898,0.961])):
            y=int(y1+yr*(y2-y1-1))
            for col,xr in enumerate([0.414,0.545,0.673,0.805,0.941]):
                x=int(x1+xr*(x2-x1-1))
                cv2.circle(img,(x,y),9,(90,90,90),2)
    # deterministic marks: Q1=C, Q16=A, Q31=E; Q23 B+C is multiple.
    for (bi,row,col) in [(0,0,2),(1,0,0),(2,0,4),(1,7,1),(1,7,2)]:
        x1,y1,x2,y2=[(48,458,268,987),(283,458,499,987),(514,458,719,987)][bi]
        y=int(y1+[0.081,0.144,0.207,0.270,0.333,0.396,0.458,0.521,0.584,0.646,0.709,0.772,0.835,0.898,0.961][row]*(y2-y1-1))
        x=int(x1+[0.414,0.545,0.673,0.805,0.941][col]*(x2-x1-1))
        cv2.circle(img,(x,y),8,(20,20,20),-1)
    return img


def test_new_template_reads_expected_marks():
    img=make_card()
    ok,enc=cv2.imencode('.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,95])
    result=scan_card(enc.tobytes())
    qs={q['number']:q for q in result['questions']}
    assert len(result['questions'])==45
    assert qs[1]['answer']=='C'
    assert qs[16]['answer']=='A'
    assert qs[31]['answer']=='E'
    assert qs[23]['status']=='MULT'
