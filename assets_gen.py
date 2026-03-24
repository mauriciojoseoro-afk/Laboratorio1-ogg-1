

"""
Asset Generator - Carga imágenes desde carpetas.
Si no encuentra las imágenes, genera gráficos simples de respaldo.
"""

import pygame
import os

# Rutas de carpetas
CARPETA_ASSETS = "assets"
CARPETA_JUGADOR = os.path.join(CARPETA_ASSETS, "player")
CARPETA_OBSTACULOS = os.path.join(CARPETA_ASSETS, "obstacles")
CARPETA_POWERUPS = os.path.join(CARPETA_ASSETS, "powerups")
CARPETA_SUELO = os.path.join(CARPETA_ASSETS, "ground")
CARPETA_FONDO = os.path.join(CARPETA_ASSETS, "backgrounds")

def cargar_imagen(ruta, tamaño=None):
    """Carga imagen si existe, sino retorna None."""
    if not os.path.exists(ruta):
        return None
    try:
        img = pygame.image.load(ruta).convert_alpha()
        if tamaño:
            img = pygame.transform.scale(img, tamaño)
        return img
    except:
        return None

def generate_background(ancho=900, alto=655):
    """Fondo: intenta cargar imagen, si no hay, fondo azul simple."""
    img = cargar_imagen(os.path.join(CARPETA_FONDO, "fondo.png"), (ancho, alto))
    if img:
        return img
    
    # Respaldo simple
    surf = pygame.Surface((ancho, alto))
    surf.fill((30, 40, 80))
    return surf

def generate_player_frames(w=40, h=50):
    """Jugador: busca run1.png a run6.png y jump.png, si no hay, un rectángulo simple."""
    frames = []
    
    # Intentar cargar frames de correr
    for i in range(1, 7):
        img = cargar_imagen(os.path.join(CARPETA_JUGADOR, f"correr{i}.png"), (w, h))
        if not img:
            break
        frames.append(img)
    
    # Si cargó los 6 frames, cargar el salto
    if len(frames) == 6:
        img_salto = cargar_imagen(os.path.join(CARPETA_JUGADOR, "salto.png"), (w, h))
        if img_salto:
            return frames, img_salto
    
    # Respaldo: un cuadrito simple
    for _ in range(6):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((100, 150, 255))
        frames.append(surf)
    
    surf_salto = pygame.Surface((w, h), pygame.SRCALPHA)
    surf_salto.fill((100, 150, 255))
    return frames, surf_salto

def generate_obstacles():
    """Obstáculos: busca rock.png, spike.png, barrel.png, si no hay, cuadritos rojos."""
    obstaculos = []
    
    tipos = ["roca", "pico", "barril"]
    for tipo in tipos:
        img = cargar_imagen(os.path.join(CARPETA_OBSTACULOS, f"{tipo}.png"), (50, 45))
        if img:
            obstaculos.append((tipo, img))
        else:
            # Respaldo: cuadrado rojo
            surf = pygame.Surface((40, 35), pygame.SRCALPHA)
            surf.fill((200, 50, 50))
            obstaculos.append((tipo, surf))
    
    return obstaculos

def generate_powerup():
    """Power-up: busca powerup.png, si no hay, estrella amarilla simple."""
    img = cargar_imagen(os.path.join(CARPETA_POWERUPS, "powerup.png"), (40, 40))
    if img:
        return img
    
    # Respaldo: círculo dorado
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 200, 0), (16, 16), 14)
    return surf

def generate_ground_tile(ancho=800, alto=100
                         
                         ):
    """Tile del suelo: busca suelo.png, si no hay, rectángulo verde."""
    img = cargar_imagen(os.path.join(CARPETA_SUELO, "suelo.png"), (ancho, 110))
    if img:
        return img
    
    # Respaldo: rectángulo verde
    surf = pygame.Surface((ancho, alto))
    surf.fill((50, 120, 50))
    return surf

def generate_invincible_player_frames(w=40, h=50):
    """Jugador invencible: usa los mismos frames pero con brillo, o los normales."""
    frames_normales, _ = generate_player_frames(w, h)
    # Para invencible, devolvemos los mismos frames (ya tendrás un efecto aparte)
    return frames_normales

def generate_particle(color=(255, 200, 50), tamaño=8):
    """Partícula: círculo simple."""
    surf = pygame.Surface((tamaño * 2, tamaño * 2), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (tamaño, tamaño), tamaño)
    return surf

