# Conector AWS DynamoDB API (CON-067)

Conector Ruvic de operaciones directas sobre una tabla de AWS DynamoDB.
Permite escribir/reemplazar un ítem, obtenerlo por clave, consultar por
partition key, eliminarlo y describir la tabla.

## Instalación

```bash
pip install git+https://github.com/Dgirto/AWS-DynamoDB-API.git#subdirectory=lib
```

Python 3.10+. Dependencia única: `boto3>=1.34,<2.0`.

## Permisos requeridos en AWS (IAM)

Crea un usuario o rol IAM con una policy limitada a la tabla configurada:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/mi-tabla",
        "arn:aws:dynamodb:*:*:table/mi-tabla/index/*"
      ]
    }
  ]
}
```

No se otorgan permisos de administración (`dynamodb:CreateTable`,
`dynamodb:DeleteTable`, `dynamodb:UpdateTable`, etc.).

## Variables de entorno (`RUVIC_DYNAMODB_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_DYNAMODB_ACCESS_KEY_ID` | Sí | Access Key ID de AWS |
| `RUVIC_DYNAMODB_SECRET_ACCESS_KEY` | Sí | Secret Access Key de AWS |
| `RUVIC_DYNAMODB_REGION` | Sí | Región de AWS (ej. `us-east-1`) |
| `RUVIC_DYNAMODB_TABLE` | Sí | Nombre de la tabla |
| `RUVIC_DYNAMODB_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_DYNAMODB_ACCESS_KEY_ID=tu-access-key
export RUVIC_DYNAMODB_SECRET_ACCESS_KEY=tu-secret-key
export RUVIC_DYNAMODB_REGION=us-east-1
export RUVIC_DYNAMODB_TABLE=mi-tabla-de-prueba

python test_connection.py
python validate_local.py
```

La tabla de prueba debe tener una partition key simple llamada `id`
(tipo string) para que `validate_local.py` funcione tal cual.

## Notas de integración

- Este conector **SÍ escribe y elimina** datos reales en la tabla
  configurada (`put_item` y `delete_item`). No es de solo lectura.
- `put_item` **reemplaza el ítem completo** si ya existe una clave
  igual — no hace un merge parcial de atributos.
- `query` requiere el nombre exacto del atributo de partition key de la
  tabla o del índice (GSI/LSI); si se pasa un índice, `index_name` debe
  coincidir con el nombre configurado en DynamoDB.
- Los tipos de dato de DynamoDB (String, Number, Binary, etc.) se
  traducen automáticamente hacia/desde tipos nativos de Python gracias
  a la interfaz de alto nivel (`boto3.resource`), no la de bajo nivel.
