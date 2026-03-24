# JUMPER - Space Runner 🚀

Juego de plataformas runner desarrollado en Python con Pygame.

## Requisitos
```
pip install pygame numpy
```

## Cómo ejecutar
```
cd jumper_game
python main.py
```

## Estructura del Proyecto
```
jumper_game/
├── main.py         # Lógica principal del juego + máquina de estados
├── hash_table.py   # Tabla hash con doble hashing, rehashing y manejo de colisiones
├── assets_gen.py   # Generación procedural de gráficos (sin archivos externos)
└── jumper_save.json  # (se crea automáticamente al guardar)
```

## Conceptos de Estructuras de Datos Implementados

### Tabla Hash con Doble Hashing
- **Hash primario**: h(k) = Σ(31^i * char_i) mod capacity
- **Hash secundario** (para resolución de colisiones): h2(k) = Σ(37^i * char_i) mod (capacity - 1)
- **Probe sequence**: index(k, i) = (h(k) + i * h2(k)) mod capacity

### Rehashing
- Se activa cuando: `(size + deleted) / capacity >= 0.7`
- Nueva capacidad = capacidad actual × 2
- Todos los elementos se reinsertan en la nueva tabla
- Ejemplo: 7 → 14 → 28 → 56...

### Manejo de Colisiones
- **Doble hashing** como resolución de colisiones
- **Lazy deletion** para eliminaciones (marca como deleted sin borrar físicamente)

### Estructura de Archivos
- Persistencia en JSON via `jumper_save.json`
- Formato: `{ "capacity": N, "users": { "nombre": { datos } } }`

## Mecánicas de Juego
- **Niveles**: 3 niveles con velocidad creciente
  - Nivel 1: 2000m, velocidad baja
  - Nivel 2: 2500m, velocidad media  
  - Nivel 3: 3000m, velocidad alta
- **Power-up**: Estrella dorada → 3 segundos de invencibilidad
- **Obstáculos**: Rocas, picos, barriles
- **Vidas**: 3 vidas por partida
- **Progresión**: Niveles se desbloquean al completar el anterior

## Controles
- **ESPACIO / ↑**: Saltar
- **ESC**: Volver al menú de niveles
- **Mouse**: Navegar menús
