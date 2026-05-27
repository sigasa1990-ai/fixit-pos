from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Permiso denegado"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflicto"):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class InsufficientStockException(AppException):
    def __init__(self, product_name: str):
        super().__init__(
            detail=f"Stock insuficiente para: {product_name}",
            status_code=status.HTTP_409_CONFLICT,
        )


class CashRegisterClosedException(AppException):
    def __init__(self):
        super().__init__(
            detail="La caja debe estar abierta para realizar esta operación",
            status_code=status.HTTP_409_CONFLICT,
        )


class TenantIsolationException(AppException):
    def __init__(self):
        super().__init__(
            detail="Acceso denegado: datos de otro tenant",
            status_code=status.HTTP_403_FORBIDDEN,
        )
