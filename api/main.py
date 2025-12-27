from fastapi import FastAPI

from api.db import apply_migrations

from api.routers import common_backend, line_prince, stripe, tg_prince

app = FastAPI()


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def run_migrations() -> None:
    apply_migrations()


app.include_router(line_prince.router)
app.include_router(stripe.router)
app.include_router(tg_prince.router)
app.include_router(common_backend.router)
