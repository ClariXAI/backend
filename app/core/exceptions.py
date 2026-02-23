from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    def __init__(self, resource: str, resource_id: str | None = None):
        self.resource = resource
        self.resource_id = resource_id


class ForbiddenError(Exception):
    pass


class ConflictError(Exception):
    def __init__(self, detail: str):
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        detail = f"{exc.resource} não encontrado"
        if exc.resource_id:
            detail = f"{exc.resource} '{exc.resource_id}' não encontrado"
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": detail})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Acesso negado"},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.detail},
        )
