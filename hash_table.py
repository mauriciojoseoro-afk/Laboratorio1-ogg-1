"""
Tabla Hash con Rehashing y Manejo de Colisiones mediante Doble Hashing.
Almacena datos de jugadores: nombre_usuario -> {puntaje por nivel, niveles desbloqueados}
"""

import json
import os

UMBRAL_FACTOR_CARGA = 0.7  # Rehash cuando el 70% de la capacidad está ocupada


class HashEntry:
    """Entrada individual de la tabla hash con soporte de eliminación lógica."""
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.deleted = False  # Marca de eliminación lógica (lazy deletion)


class HashMap:
    """Tabla hash con doble hashing, rehashing automático y persistencia en JSON."""

    def __init__(self, initial_capacity=7):
        self.capacity = initial_capacity
        self.size = 0
        self.table = [None] * self.capacity
        self.deleted_count = 0

    def _hash(self, key):
        """Hash primario: polinomio de Horner con base 31."""
        h = 0
        for caracter in key:
            h = (h * 31 + ord(caracter)) % self.capacity
        return h

    def _hash2(self, key):
        """Hash secundario para doble hashing (base 37). Mínimo retorna 1."""
        h = 0
        for caracter in key:
            h = (h * 37 + ord(caracter)) % (self.capacity - 1)
        return max(1, h)

    def _probe(self, key, i):
        """Calcula el índice del i-ésimo intento: (hash1 + i * hash2) % capacidad."""
        return (self._hash(key) + i * self._hash2(key)) % self.capacity

    def _needs_rehash(self):
        """Retorna True si la ocupación supera el umbral del factor de carga."""
        return (self.size + self.deleted_count) / self.capacity >= UMBRAL_FACTOR_CARGA

    def _rehash(self):
        """Duplica la capacidad y reinserta todas las entradas activas."""
        tabla_anterior = self.table
        capacidad_anterior = self.capacity
        self.capacity = self.capacity * 2
        self.table = [None] * self.capacity
        self.size = 0
        self.deleted_count = 0
        print(f"[REHASH] Capacity: {capacidad_anterior} -> {self.capacity}")
        for entrada in tabla_anterior:
            if entrada is not None and not entrada.deleted:
                self._insert_raw(entrada.key, entrada.value)

    def _insert_raw(self, key, value):
        """Inserción interna sin verificar rehash. Usada al reconstruir la tabla."""
        for intento in range(self.capacity):
            idx = self._probe(key, intento)
            if self.table[idx] is None or self.table[idx].deleted:
                self.table[idx] = HashEntry(key, value)
                self.size += 1
                return True
            elif self.table[idx].key == key:
                self.table[idx].value = value
                return True
        return False

    def insert(self, key, value):
        """Inserta una nueva entrada o actualiza el valor si la clave ya existe."""
        if self._needs_rehash():
            self._rehash()
        existente = self.get(key)
        if existente is not None:
            for intento in range(self.capacity):
                idx = self._probe(key, intento)
                if self.table[idx] is not None and not self.table[idx].deleted and self.table[idx].key == key:
                    self.table[idx].value = value
                    return
        for intento in range(self.capacity):
            idx = self._probe(key, intento)
            if self.table[idx] is None or self.table[idx].deleted:
                estaba_eliminado = self.table[idx] is not None and self.table[idx].deleted
                self.table[idx] = HashEntry(key, value)
                self.size += 1
                if estaba_eliminado:
                    self.deleted_count -= 1
                return

    def get(self, key):
        """Busca y retorna el valor asociado a la clave. Retorna None si no existe."""
        for intento in range(self.capacity):
            idx = self._probe(key, intento)
            if self.table[idx] is None:
                return None
            if not self.table[idx].deleted and self.table[idx].key == key:
                return self.table[idx].value
        return None

    def delete(self, key):
        """Elimina lógicamente una entrada. Retorna True si fue encontrada."""
        for intento in range(self.capacity):
            idx = self._probe(key, intento)
            if self.table[idx] is None:
                return False
            if not self.table[idx].deleted and self.table[idx].key == key:
                self.table[idx].deleted = True
                self.size -= 1
                self.deleted_count += 1
                return True
        return False

    def get_all_users(self):
        """Retorna lista de tuplas (clave, valor) de todas las entradas activas."""
        usuarios = []
        for entrada in self.table:
            if entrada is not None and not entrada.deleted:
                usuarios.append((entrada.key, entrada.value))
        return usuarios

    def user_exists(self, key):
        """Retorna True si el usuario existe en la tabla."""
        return self.get(key) is not None

    def update_username(self, old_key, new_key):
        """Renombra un usuario. Falla si old_key no existe o new_key ya está en uso."""
        valor = self.get(old_key)
        if valor is None:
            return False
        if self.user_exists(new_key):
            return False
        self.delete(old_key)
        self.insert(new_key, valor)
        return True

    def to_dict(self):
        """Serializa la tabla a un diccionario con capacidad y usuarios activos."""
        return {
            "capacity": self.capacity,
            "users": {k: v for k, v in self.get_all_users()}
        }

    def from_dict(self, data):
        """Reconstruye la tabla desde un diccionario serializado."""
        self.capacity = data.get("capacity", 7)
        self.table = [None] * self.capacity
        self.size = 0
        self.deleted_count = 0
        for key, value in data.get("users", {}).items():
            self._insert_raw(key, value)

    def save_to_file(self, filepath="save_data.json"):
        """Guarda el estado actual de la tabla en un archivo JSON."""
        with open(filepath, "w") as archivo:
            json.dump(self.to_dict(), archivo, indent=2)

    def load_from_file(self, filepath="save_data.json"):
        """Carga el estado desde un archivo JSON. Retorna False si falla."""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r") as archivo:
                datos = json.load(archivo)
            self.from_dict(datos)
            return True
        except Exception as error:
            print(f"[LOAD ERROR] {error}")
            return False


def default_user_data():
    """Retorna datos iniciales de un jugador nuevo con solo el nivel 1 desbloqueado."""
    return {
        "level1_score": 0,
        "level2_score": 0,
        "level3_score": 0,
        "levels_unlocked": 1
    }