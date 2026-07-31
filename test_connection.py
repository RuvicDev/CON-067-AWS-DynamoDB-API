"""Prueba de conexión estándar del conector dynamodb.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_DYNAMODB_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta a DynamoDB y describe la tabla configurada usando las env
    vars RUVIC_DYNAMODB_*."""
    try:
        from ruvic_dynamodb_connector import (
            DynamodbAuthError,
            DynamodbClient,
            DynamodbDataError,
            DynamodbNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-dynamodb-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "AWS-DynamoDB-API.git#subdirectory=lib",
        )

    try:
        client = DynamodbClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except DynamodbAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except DynamodbNetworkError as exc:
        return False, f"Error de red: {exc}"
    except DynamodbDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a la tabla DynamoDB {client.config.table!r} en {client.config.region!r}",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
