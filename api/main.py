from fastapi import FastAPI

from api.routers import line_prince, stripe, tg_prince

app = FastAPI()


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(line_prince.router)
app.include_router(stripe.router)
app.include_router(tg_prince.router)
