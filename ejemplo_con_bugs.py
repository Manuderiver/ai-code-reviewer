"""Archivo de ejemplo con problemas intencionales para probar el reviewer."""


def dividir(a, b):
    return a / b  # no controla división por cero


def buscar_usuario(lista_usuarios, id):
    for u in lista_usuarios:
        if u['id'] == id:
            return u
    # no retorna nada si no lo encuentra -> devuelve None sin avisar


class Contador:
    total = 0  # atributo de clase usado como si fuera de instancia

    def sumar(self, valor):
        self.total += valor
        return self.total


def leer_archivo(ruta):
    archivo = open(ruta, 'r')  # no se cierra el archivo ni usa "with"
    contenido = archivo.read()
    return contenido
