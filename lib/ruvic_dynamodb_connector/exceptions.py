"""Excepciones propias del conector DynamoDB.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del SDK subyacente.
"""


class DynamodbConnectorError(Exception):
    """Error base del conector."""


class DynamodbAuthError(DynamodbConnectorError):
    """Credenciales inválidas o permisos IAM insuficientes."""


class DynamodbNetworkError(DynamodbConnectorError):
    """No se pudo alcanzar el servicio DynamoDB (red/timeout)."""


class DynamodbDataError(DynamodbConnectorError):
    """La operación es válida pero la tabla/ítem es inválido."""
