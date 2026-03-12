from fastapi import APIRouter

router = APIRouter(tags=["core"])

@router.get("/")
def read_root():
    return {"message": "API is running ok", "version": "0.1.0"}

@router.get("/healthz")
def health_check():
    return {"status": "ok"}