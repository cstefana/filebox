import uvicorn
from fastapi import FastAPI
from db.database import engine, Base
from api.routes import user_routes

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(user_routes.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


def main():
    print("Hello from filebox!")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
