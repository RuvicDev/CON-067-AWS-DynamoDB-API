"""Validación local del conector dynamodb: ejercita las 5 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_DYNAMODB_* exportadas en el entorno, con
una tabla de prueba cuya partition key sea "id" (string).

ADVERTENCIA: este script escribe y elimina un ítem REAL en la tabla
configurada. Ejecútalo solo contra una tabla de pruebas.
"""

from ruvic_dynamodb_connector import DynamodbClient, setup_logging

setup_logging("INFO")
client = DynamodbClient()

print("== 1. Describir tabla ==")
info = client.describe_table()
print(f"  {info['name']}: {info['status']}, {info['item_count']} ítems")

print("== 2. Escribir ítem ==")
client.put_item({"id": "ruvic-test-1", "nombre": "ACME Corp", "ciudad": "Bogota"})
print("  escrito")

print("== 3. Leer ítem ==")
item = client.get_item({"id": "ruvic-test-1"})
print(f"  {item}")

print("== 4. Consultar por partition key ==")
resultados = client.query("id", "ruvic-test-1")
print(f"  {len(resultados)} ítem(s)")

print("== 5. Eliminar ítem ==")
client.delete_item({"id": "ruvic-test-1"})
print("  eliminado")

print("\nTodo OK: describe_table, put_item, get_item, query y delete_item funcionan.")
