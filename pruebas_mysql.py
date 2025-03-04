import unittest
from components.database_mysql_component import DataBaseMySQLManager
from datetime import datetime

class TestDataBaseMySQLManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """ Configurar conexión a MySQL antes de todas las pruebas """
        cls.db_manager = DataBaseMySQLManager()

    def test_insertar_cliente(self):
        """ Prueba insertar un nuevo cliente en MySQL """
        documento_identidad = "12345678"
        tipo_documento = "DNI"
        nombre = "Juan"
        apellido = "Pérez"
        celular = "+51987654321"
        email = "juan.perez@example.com"
        estado = "nuevo"

        # Insertar cliente
        cliente_id = self.db_manager.insertar_cliente(documento_identidad, tipo_documento, nombre, apellido, celular, email, estado)

        # Verificar que se insertó correctamente
        self.assertIsInstance(cliente_id, int, "El ID del cliente debería ser un entero.")
        print(f"Cliente insertado correctamente con ID: {cliente_id}")

    def test_obtener_id_cliente_por_dni(self):
        """ Prueba obtener el ID de un cliente usando su DNI """
        dni = "12345678"

        # Obtener ID del cliente
        cliente_id = self.db_manager.obtener_id_cliente_por_dni(dni)

        # Verificar que se obtuvo un ID válido
        self.assertIsInstance(cliente_id, int, "El ID del cliente debería ser un entero.")
        print(f"ID del cliente obtenido correctamente: {cliente_id}")

    def test_insertar_codigoPago(self):
        """ Prueba insertar un código de pago en MySQL """
        cliente_id = self.db_manager.obtener_id_cliente_por_dni("12345678")  # Obtener cliente de prueba
        self.assertIsNotNone(cliente_id, "El cliente no debería ser None para insertar un código de pago.")

        codigo = "ABC123456"
        tipo_codigo = "recaudacion"
        caso_relacionado = "Caso de prueba"
        fecha_asignacion = datetime.now()

        # Insertar código de pago
        codigo_id = self.db_manager.insertar_codigoPago(cliente_id, codigo, tipo_codigo, caso_relacionado, fecha_asignacion)

        # Verificar que se insertó correctamente
        self.assertIsInstance(codigo_id, int, "El ID del código de pago debería ser un entero.")
        print(f"Código de pago insertado correctamente con ID: {codigo_id}")


    def test_obtener_datos_codigoPago(self):
        """ Prueba obtener los datos de un código de pago existente """
        codigo = "ABC123456"  # Código previamente insertado en test_insertar_codigoPago

        # Obtener los datos del código de pago
        datos_codigo = self.db_manager.obtener_datos_codigoPago(codigo)

        # Verificar que se obtuvieron datos válidos
        self.assertIsNotNone(datos_codigo, "Los datos del código de pago no deberían ser None.")
        self.assertEqual(datos_codigo["codigo"], codigo, "El código obtenido debería coincidir con el insertado.")
        print(f"Datos del código de pago obtenidos correctamente: {datos_codigo}")

if __name__ == "__main__":
    unittest.main()
