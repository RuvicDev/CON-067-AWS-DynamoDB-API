---
name: dynamodb
description: >
  Usa la librería ruvic_dynamodb_connector para operar directamente
  sobre una tabla de AWS DynamoDB - escribir/reemplazar un ítem
  (put_item), obtener un ítem por clave (get_item), consultar por
  partition key (query), eliminar un ítem (delete_item), y describir
  la tabla (describe_table). Úsala cuando el usuario pida leer, guardar
  o eliminar datos en DynamoDB.
triggers:
- dynamodb
- dynamo
- aws dynamodb
- tabla nosql
- item dynamodb
---

# Conector AWS DynamoDB API (ruvic_dynamodb_connector)

Librería Python de operaciones directas sobre DynamoDB. Está
**preinstalada en el runtime** cuando el conector está configurado (si
no, instálala con `pip install git+https://github.com/Dgirto/AWS-DynamoDB-API.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de
variables de entorno, disponibles cuando el conector `dynamodb` está
configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_DYNAMODB_ACCESS_KEY_ID` | Access Key ID de AWS |
| `RUVIC_DYNAMODB_SECRET_ACCESS_KEY` | Secret Access Key de AWS |
| `RUVIC_DYNAMODB_REGION` | Región de AWS |
| `RUVIC_DYNAMODB_TABLE` | Nombre de la tabla |
| `RUVIC_DYNAMODB_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no
generes código que lo use; indica al usuario que lo configure en
**Settings → Conectores**.

## Este conector SÍ escribe y elimina

A diferencia de los conectores de solo consulta, `dynamodb` escribe
(`put_item`) y elimina (`delete_item`) ítems reales en la tabla
configurada. Confirma con el usuario antes de escribir o eliminar un
ítem si la acción no fue explícitamente solicitada.

## Conexión (siempre igual)

```python
from ruvic_dynamodb_connector import DynamodbClient

client = DynamodbClient()  # lee RUVIC_DYNAMODB_* del entorno automáticamente
```

## Capacidad 1 — Escribir/reemplazar un ítem

```python
client.put_item({"id": "123", "nombre": "ACME Corp", "ciudad": "Bogota"})
```

`put_item` reemplaza el ítem completo si la clave ya existe.

## Capacidad 2 — Obtener un ítem por clave

```python
item = client.get_item({"id": "123"})  # None si no existe
```

## Capacidad 3 — Consultar por partition key

```python
resultados = client.query("customer_id", "C-100")
# con un índice secundario:
resultados = client.query("status", "PENDING", index_name="status-index")
```

## Capacidad 4 — Eliminar un ítem

```python
client.delete_item({"id": "123"})
```

## Capacidad 5 — Describir la tabla

```python
info = client.describe_table()
print(info["status"], info["item_count"])
```

## Manejo de errores

```python
from ruvic_dynamodb_connector import (
    DynamodbAuthError, DynamodbDataError, DynamodbNetworkError,
)

try:
    client.put_item({"id": "123", "nombre": "ACME Corp"})
except DynamodbAuthError:
    print("Credenciales inválidas o sin permiso IAM suficiente")
except DynamodbNetworkError:
    print("No se pudo alcanzar DynamoDB — reintenta en unos segundos")
except DynamodbDataError as e:
    print(f"Error de datos: {e}")  # ej. la tabla no existe o falta la clave
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_DYNAMODB_*` (el constructor de `DynamodbClient` ya lo hace).
2. Nunca imprimas `RUVIC_DYNAMODB_SECRET_ACCESS_KEY` en logs ni en la salida.
3. Este conector modifica datos reales: no escribas ni elimines ítems sin que el usuario lo haya pedido explícitamente.
4. Para `query`, confirma primero el nombre real del atributo de partition key (de la tabla o del índice) con el usuario si no es obvio por el contexto.
5. `put_item` reemplaza el ítem completo — si el usuario solo quiere actualizar un atributo, primero leelo con `get_item`, modificá el campo, y recién ahí llamá a `put_item` con el ítem completo.
