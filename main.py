import uvicorn
from fastapi import FastAPI
from api.lifespan import lifespan
from db.database import engine, Base
from api.routes import auth_router, core_router, files_router
Base.metadata.create_all(bind=engine)

app = FastAPI(lifespan=lifespan)

app.include_router(core_router)
app.include_router(auth_router)
app.include_router(files_router)


def main():
    print("Hello from filebox!")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
