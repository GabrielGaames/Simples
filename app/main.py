from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .scanner import ScanError, scan_card

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="EDUSCANNER Simples")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/scan")
async def scan(file: UploadFile = File(...)):
    try:
        content = await file.read()
        result = scan_card(content)
        return result
    except ScanError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"detail": "Não foi possível processar a foto. Tente outra imagem."},
        )
