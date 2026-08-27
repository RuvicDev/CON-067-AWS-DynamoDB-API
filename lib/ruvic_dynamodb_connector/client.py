"""Cliente de operaciones directas para AWS DynamoDB.

Capacidades:
- put_item():        escribir/reemplazar un ítem.
- get_item():         obtener un ítem por su clave.
- query():            consultar ítems por partition key (e índice opcional).
- delete_item():      eliminar un ítem por su clave.
- describe_table():   metadatos de la tabla (claves, estado, tamaño).

Las credenciales SIEMPRE provienen de variables de entorno
RUVIC_DYNAMODB_* (ver config.DynamodbConfig.from_env). Prohibido
hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import boto3  # type: ignore[import-untyped]
from boto3.dynamodb.conditions import Key  # type: ignore[import-untyped]
from botocore.config import Config as BotoConfig  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
)

from .config import DynamodbConfig
from .exceptions import (
    DynamodbAuthError,
    DynamodbConnectorError,
    DynamodbDataError,
    DynamodbNetworkError,
)
from .logging_utils import get_logger

_AUTH_ERROR_CODES = {
    "AccessDeniedException",
    "UnrecognizedClientException",
    "InvalidClientTokenId",
    "InvalidSignatureException",
}
_NOT_FOUND_ERROR_CODES = {"ResourceNotFoundException"}
_MAX_QUERY_LIMIT = 500


def _wrap_client_error(exc: ClientError, not_found_message: str) -> DynamodbConnectorError:
    """Traduce un error de la API de AWS a una excepción propia, sin dejar
    escapar nunca el tipo crudo del SDK."""
    code = exc.response.get("Error", {}).get("Code", "")
    if code in _AUTH_ERROR_CODES:
        return DynamodbAuthError(
            "Credenciales inválidas o sin permiso IAM suficiente para esta "
            "operación. Revisa la policy adjunta al usuario o rol."
        )
    if code in _NOT_FOUND_ERROR_CODES:
        return DynamodbDataError(not_found_message)
    if code == "ValidationException":
        return DynamodbDataError(f"Parámetro inválido: {exc}")
    if code == "ConditionalCheckFailedException":
        return DynamodbDataError("La condición de la escritura no se cumplió.")
    return DynamodbDataError(f"Error de datos ({code}): {exc}")


class DynamodbClient:
    """Cliente de operaciones directas sobre una tabla de AWS DynamoDB.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_DYNAMODB_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = DynamodbClient()  # lee RUVIC_DYNAMODB_* del entorno
        >>> client.get_item({"id": "123"})
        {'id': '123', 'nombre': 'ACME Corp', ...}
    """

    def __init__(self, config: DynamodbConfig | None = None) -> None:
        self.config = config or DynamodbConfig.from_env()
        self._logger = get_logger()
        self._table: Any = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_table(self) -> Any:
        if self._table is not None:
            return self._table
        resource = boto3.resource(
            "dynamodb",
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key,
            region_name=self.config.region,
            config=BotoConfig(
                connect_timeout=self.config.connect_timeout,
                read_timeout=max(self.config.connect_timeout, 30),
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )
        self._table = resource.Table(self.config.table)
        return self._table

    def ping(self) -> bool:
        """Verifica la conexión describiendo la tabla configurada.

        Returns:
            True si la conexión funciona.

        Raises:
            DynamodbAuthError / DynamodbNetworkError / DynamodbDataError.
        """
        self.describe_table()
        self._logger.info("Ping exitoso a DynamoDB, tabla %s", self.config.table)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: escribir/reemplazar un ítem
    # ------------------------------------------------------------------ #

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Escribe (o reemplaza por completo) un ítem en la tabla.

        Args:
            item: diccionario con el ítem completo, incluyendo la(s)
                clave(s) primaria(s) de la tabla.

        Returns:
            El mismo ítem escrito.

        Ejemplo:
            >>> client.put_item({"id": "123", "nombre": "ACME Corp"})
            {'id': '123', 'nombre': 'ACME Corp'}
        """
        if not item:
            raise DynamodbDataError("item no puede estar vacío.")
        table = self._get_table()
        try:
            table.put_item(Item=item)
        except ClientError as exc:
            raise _wrap_client_error(exc, "No se pudo escribir el ítem.") from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise DynamodbNetworkError(f"No se pudo escribir el ítem: {exc}") from exc
        self._logger.info("Ítem escrito en tabla %s", self.config.table)
        return item

    # ------------------------------------------------------------------ #
    # Capacidad 2: obtener un ítem por clave
    # ------------------------------------------------------------------ #

    def get_item(self, key: dict[str, Any]) -> dict[str, Any] | None:
        """Obtiene un ítem por su clave primaria.

        Args:
            key: diccionario con la(s) clave(s) primaria(s) del ítem
                (ej. {"id": "123"} o {"pk": "123", "sk": "2026-01-01"}).

        Returns:
            El ítem encontrado, o None si no existe.

        Ejemplo:
            >>> client.get_item({"id": "123"})
            {'id': '123', 'nombre': 'ACME Corp'}
        """
        if not key:
            raise DynamodbDataError("key no puede estar vacío.")
        table = self._get_table()
        try:
            response = table.get_item(Key=key)
        except ClientError as exc:
            raise _wrap_client_error(exc, "No se pudo leer el ítem.") from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise DynamodbNetworkError(f"No se pudo leer el ítem: {exc}") from exc
        item = response.get("Item")
        self._logger.info("Ítem %s en tabla %s", "encontrado" if item else "no encontrado", self.config.table)
        return item

    # ------------------------------------------------------------------ #
    # Capacidad 3: consultar por partition key
    # ------------------------------------------------------------------ #

    def query(
        self,
        partition_key_name: str,
        partition_key_value: Any,
        index_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Consulta ítems que comparten una partition key.

        Args:
            partition_key_name: nombre del atributo de partition key (de
                la tabla o del índice secundario).
            partition_key_value: valor a buscar.
            index_name: nombre de un índice secundario global/local
                (GSI/LSI) opcional. Si se omite, consulta la tabla base.
            limit: máximo de ítems a retornar (default 50, máximo 500).

        Returns:
            Lista de ítems que coinciden con la partition key.

        Ejemplo:
            >>> client.query("customer_id", "C-100")
            [{'customer_id': 'C-100', 'order_id': 'O-1', ...}, ...]
        """
        if partition_key_name is not None and not isinstance(partition_key_name, str):
            raise DynamodbDataError(
                f"partition_key_name debe ser un string, no {type(partition_key_name).__name__}."
            )
        partition_key_name = (partition_key_name or "").strip()
        if not partition_key_name:
            raise DynamodbDataError("partition_key_name no puede estar vacío.")
        try:
            limit = max(1, min(int(limit), _MAX_QUERY_LIMIT))
        except (TypeError, ValueError) as exc:
            raise DynamodbDataError(f"limit inválido: {limit!r}. Debe ser un número entero.") from exc
        table = self._get_table()
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key(partition_key_name).eq(partition_key_value),
            "Limit": limit,
        }
        if index_name:
            kwargs["IndexName"] = index_name
        try:
            response = table.query(**kwargs)
        except ClientError as exc:
            raise _wrap_client_error(exc, "No se pudo ejecutar la consulta.") from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise DynamodbNetworkError(f"No se pudo ejecutar la consulta: {exc}") from exc
        items = response.get("Items", [])
        self._logger.info("Query retornó %d ítem(s) en tabla %s", len(items), self.config.table)
        return items

    # ------------------------------------------------------------------ #
    # Capacidad 4: eliminar un ítem
    # ------------------------------------------------------------------ #

    def delete_item(self, key: dict[str, Any]) -> None:
        """Elimina un ítem por su clave primaria.

        Args:
            key: diccionario con la(s) clave(s) primaria(s) del ítem.

        Ejemplo:
            >>> client.delete_item({"id": "123"})
        """
        if not key:
            raise DynamodbDataError("key no puede estar vacío.")
        table = self._get_table()
        try:
            table.delete_item(Key=key)
        except ClientError as exc:
            raise _wrap_client_error(exc, "No se pudo eliminar el ítem.") from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise DynamodbNetworkError(f"No se pudo eliminar el ítem: {exc}") from exc
        self._logger.info("Ítem eliminado de tabla %s", self.config.table)

    # ------------------------------------------------------------------ #
    # Capacidad 5: describir la tabla
    # ------------------------------------------------------------------ #

    def describe_table(self) -> dict[str, Any]:
        """Obtiene metadatos de la tabla configurada.

        Returns:
            Dict con: name, status, item_count, size_bytes, key_schema.

        Ejemplo:
            >>> client.describe_table()
            {'name': 'ruvic-test-table', 'status': 'ACTIVE', 'item_count': 3, ...}
        """
        table = self._get_table()
        try:
            table.reload()
        except ClientError as exc:
            raise _wrap_client_error(
                exc, f"La tabla {self.config.table!r} no existe o no es accesible."
            ) from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise DynamodbNetworkError(f"No se pudo describir la tabla: {exc}") from exc
        return {
            "name": table.table_name,
            "status": table.table_status,
            "item_count": table.item_count,
            "size_bytes": table.table_size_bytes,
            "key_schema": table.key_schema,
        }
