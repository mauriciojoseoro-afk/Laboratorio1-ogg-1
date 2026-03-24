"""
JUMPER GAME - Punto de entrada principal
Juego runner con Pygame: gestión de usuarios con tabla hash, niveles, power-ups, leaderboard y settings.
"""

import pygame
import sys
import math
import random
import time
import os
import asyncio
from hash_table import HashMap, default_user_data
from assets_gen import (
    generate_background, generate_player_frames, generate_obstacles,
    generate_powerup, generate_invincible_player_frames,
    generate_ground_tile, generate_particle
)

# ─── CONSTANTES ───────────────────────────────────────────────────────────────
ANCHO, ALTO = 800, 600
FPS = 60
SUELO_Y = 490
JUGADOR_X = 120

CONFIGURACION_NIVELES = {
    1: {"velocidad": 7,  "distancia": 2000, "intervalo_obs": 90, "nombre": "NIVEL 1"},
    2: {"velocidad": 9,  "distancia": 2500, "intervalo_obs": 65, "nombre": "NIVEL 2"},
    3: {"velocidad": 12, "distancia": 3000, "intervalo_obs": 45, "nombre": "NIVEL 3"},
}

GRAVEDAD = 0.9

FUERZA_SALTO = -12





COLORES = {
    "fondo_oscuro":   (12, 18, 35),
    "fondo_medio":    (20, 30, 60),
    "acento":         (80, 200, 255),
    "acento2":        (255, 180, 50),
    "blanco":         (240, 245, 255),
    "gris":           (100, 110, 130),
    "gris_oscuro":    (50, 55, 70),
    "verde":          (60, 200, 100),
    "rojo":           (220, 70, 70),
    "panel":          (55, 20, 20),
    "borde_panel":    (60, 100, 180),
    "bloqueado":      (50, 50, 65),
    "texto_bloq":     (80, 85, 100),
    "dorado":         (255, 215, 50),
    "invencible":     (255, 220, 50),
}

ARCHIVO_GUARDADO = "jumper_save.json"


# ─── CLASE PRINCIPAL ──────────────────────────────────────────────────────────
class JuegoJumper:
    """Clase principal del juego. Gestiona la máquina de estados, el renderizado y la lógica."""
 
    def __init__(self):
        """Inicializa Pygame, la pantalla, fuentes, tabla hash de usuarios y assets."""
        pygame.init()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("JUMPER - Space Runner")
        self.reloj = pygame.time.Clock()

        # Fuentes
        self.fuente_titulo = pygame.font.SysFont("Courier New", 56, bold=True)   # título pixel
        self.fuente_grande = pygame.font.SysFont("Segoe UI", 32)                 # resto neutral
        self.fuente_mediana = pygame.font.SysFont("Segoe UI", 22)
        self.fuente_pequena = pygame.font.SysFont("Segoe UI", 18)

        # Tabla hash de usuarios
        self.usuarios = HashMap()
        self.usuarios.load_from_file(ARCHIVO_GUARDADO)

        # Máquina de estados
        self.estado = "MENU"
        self.usuario_actual = None
        self.nivel_seleccionado = None

        # Variables de UI
        self.texto_entrada = ""
        self.entrada_activa = False
        self.mensaje = ""
        self.temporizador_mensaje = 0
        self.volumen_ajustes = 70
        self.modo_entrada_ajustes = None  # "renombrar" o None
        self.nombre_nuevo_ajustes = ""

        # Generar assets
        self._generar_assets()

        # Lista de partículas
        self.particulas = []

        # Sonidos
        self._generar_sonidos()

        # Música de fondo
        self._musica_cargada = False
        self._ruta_musica = "assets/music/musica.ogg"

        # Animación del menú
        self.tick_menu = 0

    def _generar_assets(self):
        """Genera y almacena todos los assets gráficos del juego."""
        self.fondo = generate_background(ANCHO, ALTO)
        self.jugador_correr, self.jugador_salto_img = generate_player_frames()
        self.jugador_inv = generate_invincible_player_frames()
        self.tipos_obstaculos = generate_obstacles()
        self.img_powerup = generate_powerup()
        self.tile_suelo = generate_ground_tile(ANCHO, 20)
        self.img_particula = generate_particle()

    def _generar_sonidos(self):
        """Genera sonidos simples con pygame mixer. Si numpy no está disponible, los omite."""
        self.sonidos = {}
        try:
            import numpy as np
            tasa_muestreo = 22050
            def crear_beep(frecuencia, duracion, volumen=0.3, onda="seno"):
                n = int(tasa_muestreo * duracion)
                t = np.arange(n) / tasa_muestreo
                if onda == "seno":
                    muestras = np.sin(2 * np.pi * frecuencia * t)
                elif onda == "cuadrada":
                    muestras = np.sign(np.sin(2 * np.pi * frecuencia * t)).astype(np.float32)
                else:
                    muestras = (2 * ((frecuencia * t) % 1) - 1).astype(np.float32)
                muestras *= volumen * (1 - np.arange(n) / n)
                muestras = np.clip(muestras * 32767, -32768, 32767).astype(np.int16)
                estereo = np.column_stack([muestras, muestras])
                sonido = pygame.sndarray.make_sound(estereo)
                sonido.set_volume(self.volumen_ajustes / 100)
                return sonido
            self.sonidos["salto"]   = crear_beep(440, 0.12)
            self.sonidos["morir"]   = crear_beep(220, 0.4, onda="cuadrada")
            self.sonidos["powerup"] = crear_beep(880, 0.2)
            self.sonidos["elegir"]  = crear_beep(660, 0.08)
            self.sonidos["ganar"]   = crear_beep(550, 0.5)
            print("[SONIDO] OK")
        except Exception as e:
            print(f"[SONIDO] Error: {e}")
            self.sonidos = {}

    def _reproducir(self, nombre):
        """Reproduce un sonido por nombre si está disponible."""
        if nombre in self.sonidos:
            try:
                self.sonidos[nombre].set_volume(self.volumen_ajustes / 100)
                self.sonidos[nombre].play()
            except Exception:
                pass

    # ─── HELPERS DE DIBUJO ────────────────────────────────────────────────────

    def _dibujar_fondo(self):
        """Dibuja el fondo del juego en pantalla."""
        self.pantalla.blit(self.fondo, (0, 0))

    def _dibujar_panel(self, rect, alfa=220, color_borde=None):
        """Dibuja un panel semitransparente con borde redondeado."""
        superficie = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        superficie.fill((*COLORES["panel"], alfa))
        self.pantalla.blit(superficie, (rect[0], rect[1]))
        cb = color_borde or (255, 255, 255)
        pygame.draw.rect(self.pantalla, cb, rect, 2, border_radius=8)

    def _texto(self, texto, fuente, color, x, y, centrado=True):
        """Renderiza texto en pantalla. Centrado por defecto; usar centrado=False para alineación izquierda."""
        superficie = fuente.render(texto, True, color)
        rect = superficie.get_rect()
        if centrado:
            rect.centerx, rect.centery = x, y
        else:
            rect.x, rect.y = x, y
        self.pantalla.blit(superficie, rect)
        return rect

    def _dibujar_boton(self, texto, rect, color=None, hover=False, bloqueado=False, fuente=None):
        """Botones estilo arcade con borde blanco y fondo rojo suave."""
        f = fuente or self.fuente_mediana
    
        if bloqueado:
            fondo = (120, 50, 50)       # rojo apagado
            color_texto = (150, 140, 140)
        else:
            if hover:
                fondo = (200, 80, 80)    # rojo más brillante al pasar mouse
                color_texto = (255, 255, 255)
            else:
                fondo = (180, 60, 60)    # rojo suave (no muy fuerte)
                color_texto = (255, 255, 255)  # texto blanco
    
    # Borde exterior blanco
        pygame.draw.rect(self.pantalla, (255, 255, 255), (rect[0]-2, rect[1]-2, rect[2]+4, rect[3]+4), border_radius=8)
    # Botón principal
        pygame.draw.rect(self.pantalla, fondo, rect, border_radius=6)
    # Borde interior blanco
        pygame.draw.rect(self.pantalla, (255, 255, 255), rect, 2, border_radius=6)
    
        self._texto(texto, f, color_texto, rect[0] + rect[2]//2, rect[1] + rect[3]//2)
    
    

    def _dibujar_entrada(self, etiqueta, valor, rect, activo=False):
        """Dibuja un campo de entrada de texto con cursor parpadeante cuando está activo."""
        # fondo rojo suave para el input
        pygame.draw.rect(self.pantalla, (140, 40, 40), rect, border_radius=6)
        color_borde = (220, 70, 70) if activo else (255, 255, 255)
        pygame.draw.rect(self.pantalla, color_borde, rect, 2, border_radius=6)

        mostrar = valor + ("|" if activo and int(time.time() * 2) % 2 == 0 else "")

        if etiqueta:
            self._texto(etiqueta, self.fuente_pequena, COLORES["blanco"], rect[0] + 10, rect[1] - 24, centrado=False)

        # Centrar texto del usuario dentro del campo de entrada
        superficie_texto = self.fuente_mediana.render(mostrar, True, COLORES["blanco"])
        texto_x = rect[0] + 10
        texto_y = rect[1] + (rect[3] - superficie_texto.get_height()) // 2
        self.pantalla.blit(superficie_texto, (texto_x, texto_y))

    def _mostrar_mensaje(self, mensaje, color=None, duracion=120):
        """Muestra un mensaje temporal en la parte inferior de la pantalla."""
        self.mensaje = mensaje
        self.color_mensaje = color or COLORES["acento"]
        self.temporizador_mensaje = duracion

    def _tick_mensaje(self):
        """Renderiza y decrementa el temporizador del mensaje activo."""
        if self.temporizador_mensaje > 0:
            self.temporizador_mensaje -= 1
            alfa = min(255, self.temporizador_mensaje * 4)
            superficie = self.fuente_pequena.render(self.mensaje, True, self.color_mensaje)
            self.pantalla.blit(superficie, (ANCHO//2 - superficie.get_width()//2, ALTO - 40))

    def _crear_particulas(self, x, y, color, n=12):
        """Crea n partículas en la posición indicada con velocidades y tamaños aleatorios."""
        for _ in range(n):
            angulo = random.uniform(0, 2 * math.pi)
            velocidad = random.uniform(1, 4)
            self.particulas.append({
                "x": x, "y": y,
                "vx": math.cos(angulo) * velocidad,
                "vy": math.sin(angulo) * velocidad,
                "vida": random.randint(20, 45),
                "color": color,
                "tamanio": random.randint(3, 7)
            })

    def _actualizar_particulas(self):
        """Actualiza la física y dibuja todas las partículas activas. Elimina las expiradas."""
        vivas = []
        for p in self.particulas:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.12
            p["vida"] -= 1
            if p["vida"] > 0:
                alfa = int(255 * p["vida"] / 45)
                superficie = pygame.Surface((p["tamanio"]*2, p["tamanio"]*2), pygame.SRCALPHA)
                pygame.draw.circle(superficie, (*p["color"], alfa), (p["tamanio"], p["tamanio"]), p["tamanio"])
                self.pantalla.blit(superficie, (int(p["x"]) - p["tamanio"], int(p["y"]) - p["tamanio"]))
                vivas.append(p)
        self.particulas = vivas

    # ─── ESTADO: MENÚ ─────────────────────────────────────────────────────────
    def _menu(self):
        """Renderiza y gestiona el menú principal con título animado y botones de navegación."""
        self.tick_menu += 1
        self._dibujar_fondo()

        valor_brillo = (math.sin(self.tick_menu * 0.04) + 1) / 2
        brillo = int(200 + valor_brillo * 55)  # entre 200 y 255
        color_titulo = (brillo, brillo, brillo)
        self._texto("JUMPER", self.fuente_titulo, color_titulo, ANCHO//2, 100)
            
      # En _menu(), pon los textos en blanco
        self._texto("JUMPER", self.fuente_titulo, (255, 255, 255), ANCHO//2, 100)
        self._texto("SPACE RUNNER", self.fuente_pequena, (255, 255, 255), ANCHO//2, 145)

        fotograma = self.jugador_correr[self.tick_menu // 8 % len(self.jugador_correr)]
        self.pantalla.blit(fotograma, (ANCHO//2 - 20, 160))

        mx, my = pygame.mouse.get_pos()
        botones = [
            ("START - Nueva Partida", "NUEVO_USUARIO"),
            ("CARGAR PARTIDA",        "CARGAR_USUARIO"),
            ("LEADERBOARD",           "LEADERBOARD"),
            ("SETTINGS",              "AJUSTES"),
            ("SALIR",                 "SALIR"),
        ]
        ancho_btn, alto_btn = 300, 46
        inicio_y = 250
        for i, (etiqueta, destino) in enumerate(botones):
            bx = ANCHO//2 - ancho_btn//2
            by = inicio_y + i * (alto_btn + 10)
            rect = (bx, by, ancho_btn, alto_btn)
            hover = bx <= mx <= bx+ancho_btn and by <= my <= by+alto_btn
            self._dibujar_boton(etiqueta, rect, hover=hover)

        self._tick_mensaje()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.MOUSEBUTTONDOWN:
                for i, (etiqueta, destino) in enumerate(botones):
                    bx = ANCHO//2 - ancho_btn//2
                    by = inicio_y + i * (alto_btn + 10)
                    if bx <= mx <= bx+ancho_btn and by <= my <= by+alto_btn:
                        self._reproducir("elegir")
                        if destino == "SALIR":
                            self._salir()
                        else:
                            self.texto_entrada = ""
                            self.estado = destino

    # ─── ESTADO: NUEVO USUARIO ────────────────────────────────────────────────
    def _nuevo_usuario(self):
        """Renderiza el formulario de creación de nuevo usuario."""
        self._dibujar_fondo()
        self._dibujar_panel((ANCHO//2-200, 160, 400, 260))
        self._texto("NUEVA PARTIDA", self.fuente_grande, COLORES["blanco"], ANCHO//2, 190)
        self._texto("Ingresa tu nombre de usuario:", self.fuente_pequena, COLORES["blanco"], ANCHO//2-136, 225, centrado=False)

        rect_entrada = (ANCHO//2-150, 250, 300, 44)
        self._dibujar_entrada("", self.texto_entrada, rect_entrada, activo=True)

        mx, my = pygame.mouse.get_pos()
        rect_ok   = (ANCHO//2 - 90, 315, 175, 44)
        rect_volver = (ANCHO//2 - 90, 368, 175, 40)
        hover_ok    = rect_ok[0] <= mx <= rect_ok[0]+rect_ok[2] and rect_ok[1] <= my <= rect_ok[1]+rect_ok[3]
        hover_volver = rect_volver[0] <= mx <= rect_volver[0]+rect_volver[2] and rect_volver[1] <= my <= rect_volver[1]+rect_volver[3]
        self._dibujar_boton("CREAR USUARIO", rect_ok, hover=hover_ok)
        self._dibujar_boton("< VOLVER", rect_volver, hover=hover_volver)

        self._tick_mensaje()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    self._confirmar_nuevo_usuario()
                elif evento.key == pygame.K_BACKSPACE:
                    self.texto_entrada = self.texto_entrada[:-1]
                elif evento.key == pygame.K_ESCAPE:
                    self.estado = "MENU"
                elif len(self.texto_entrada) < 18:
                    self.texto_entrada += evento.unicode
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if hover_ok:
                    self._reproducir("elegir")
                    self._confirmar_nuevo_usuario()
                if hover_volver:
                    self._reproducir("elegir")
                    self.estado = "MENU"

    def _confirmar_nuevo_usuario(self):
        """Valida el nombre ingresado, crea el usuario en la tabla hash y avanza al selector de nivel."""
        nombre = self.texto_entrada.strip()
        if not nombre:
            self._mostrar_mensaje("El nombre no puede estar vacío.", COLORES["rojo"])
            return
        if self.usuarios.user_exists(nombre):
            self._mostrar_mensaje(f"'{nombre}' ya existe. Use Cargar Partida.", COLORES["rojo"])
            return
        self.usuarios.insert(nombre, default_user_data())
        self.usuarios.save_to_file(ARCHIVO_GUARDADO)
        self.usuario_actual = nombre
        self._mostrar_mensaje(f"Bienvenido, {nombre}!", COLORES["verde"])
        print(f"[HASH TABLE] Inserted '{nombre}'. Size={self.usuarios.size}, Capacity={self.usuarios.capacity}")
        self.estado = "SELECCION_NIVEL"

    # ─── ESTADO: CARGAR USUARIO ───────────────────────────────────────────────
    def _cargar_usuario(self):
        """Renderiza el formulario para cargar una partida existente por nombre de usuario."""
        self._dibujar_fondo()
        self._dibujar_panel((ANCHO//2-200, 160, 400, 280))
        self._texto("CARGAR PARTIDA", self.fuente_grande, COLORES["blanco"], ANCHO//2, 190)
        self._texto("Ingresa tu nombre de usuario:", self.fuente_pequena, COLORES["blanco"], ANCHO//2-136, 225, centrado=False)

        rect_entrada = (ANCHO//2-150, 250, 300, 44)
        self._dibujar_entrada("", self.texto_entrada, rect_entrada, activo=True)

        mx, my = pygame.mouse.get_pos()
        rect_ok     = (ANCHO//2 - 90, 315, 175, 44)
        rect_volver = (ANCHO//2 - 90, 368, 175, 40)
        hover_ok     = rect_ok[0] <= mx <= rect_ok[0]+rect_ok[2] and rect_ok[1] <= my <= rect_ok[1]+rect_ok[3]
        hover_volver = rect_volver[0] <= mx <= rect_volver[0]+rect_volver[2] and rect_volver[1] <= my <= rect_volver[1]+rect_volver[3]
        self._dibujar_boton("CARGAR", rect_ok, hover=hover_ok)
        self._dibujar_boton("< VOLVER", rect_volver, hover=hover_volver)

        self._tick_mensaje()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    self._confirmar_cargar_usuario()
                elif evento.key == pygame.K_BACKSPACE:
                    self.texto_entrada = self.texto_entrada[:-1]
                elif evento.key == pygame.K_ESCAPE:
                    self.estado = "MENU"
                elif len(self.texto_entrada) < 18:
                    self.texto_entrada += evento.unicode
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if hover_ok:
                    self._reproducir("elegir")
                    self._confirmar_cargar_usuario()
                if hover_volver:
                    self._reproducir("elegir")
                    self.estado = "MENU"

    def _confirmar_cargar_usuario(self):
        """Verifica que el usuario exista en la tabla hash y lo establece como sesión activa."""
        nombre = self.texto_entrada.strip()
        if not nombre:
            self._mostrar_mensaje("Escribe tu nombre.", COLORES["rojo"])
            return
        if not self.usuarios.user_exists(nombre):
            self._mostrar_mensaje(f"'{nombre}' no encontrado.", COLORES["rojo"])
            return
        self.usuario_actual = nombre
        self._mostrar_mensaje(f"Bienvenido de vuelta, {nombre}!", COLORES["verde"])
        self.estado = "SELECCION_NIVEL"

    # ─── ESTADO: SELECCIÓN DE NIVEL ───────────────────────────────────────────
    def _seleccion_nivel(self):
        """Muestra los niveles disponibles, bloqueados y el mejor puntaje de cada uno."""
        self._dibujar_fondo()
        datos_usuario = self.usuarios.get(self.usuario_actual) or default_user_data()
        desbloqueados = datos_usuario.get("levels_unlocked", 1)

        self._dibujar_panel((ANCHO//2-220, 80, 440, 420))
        self._texto("SELECCIONAR NIVEL", self.fuente_grande, COLORES["blanco"], ANCHO//2, 115)
        self._texto(f"Jugador: {self.usuario_actual}", self.fuente_pequena, COLORES["blanco"], ANCHO//2, 148)

        mx, my = pygame.mouse.get_pos()
        inicio_y_niveles = 175

        for nivel in [1, 2, 3]:
            bloqueado = nivel > desbloqueados
            cfg = CONFIGURACION_NIVELES[nivel]
            bx = ANCHO//2 - 180
            by = inicio_y_niveles + (nivel - 1) * 95
            ancho_btn, alto_btn = 360, 80
            rect = (bx, by, ancho_btn, alto_btn)
            hover = not bloqueado and bx <= mx <= bx+ancho_btn and by <= my <= by+alto_btn

            if bloqueado:
                self._dibujar_boton("", rect, bloqueado=True)
                self._texto(f"🔒  {cfg['nombre']}", self.fuente_mediana, COLORES["texto_bloq"], bx + ancho_btn//2, by + 28)
                self._texto("Completa el nivel anterior para desbloquear", self.fuente_pequena, COLORES["texto_bloq"], bx + ancho_btn//2, by + 54)
            else:
                self._dibujar_boton("", rect, hover=hover)
                clave_puntaje = f"level{nivel}_score"
                mejor = datos_usuario.get(clave_puntaje, 0)
                color_nivel = COLORES["dorado"] if mejor > 0 else COLORES["blanco"]
                self._texto(cfg["nombre"], self.fuente_grande, color_nivel, bx + ancho_btn//2, by + 26)
                etiqueta_dist = f"{cfg['distancia']}m  |  Vel: {'★'*nivel}  |  Mejor: {mejor}pts"
                self._texto(etiqueta_dist, self.fuente_pequena, COLORES["blanco"], bx + ancho_btn//2, by + 54)

        rect_volver = (ANCHO//2 - 80, 510, 160, 40)
        hover_volver = rect_volver[0] <= mx <= rect_volver[0]+rect_volver[2] and rect_volver[1] <= my <= rect_volver[1]+rect_volver[3]
        self._dibujar_boton("< MENU", rect_volver, hover=hover_volver)

        self._tick_mensaje()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.MOUSEBUTTONDOWN:
                for nivel in [1, 2, 3]:
                    bloqueado = nivel > desbloqueados
                    bx = ANCHO//2 - 180
                    by = inicio_y_niveles + (nivel - 1) * 95
                    ancho_btn, alto_btn = 360, 80
                    if not bloqueado and bx <= mx <= bx+ancho_btn and by <= my <= by+alto_btn:
                        self._reproducir("elegir")
                        self.nivel_seleccionado = nivel
                        self._iniciar_juego(nivel)
                if hover_volver:
                    self._reproducir("elegir")
                    self.estado = "MENU"

    # ─── ESTADO: GAMEPLAY ─────────────────────────────────────────────────────
    def _iniciar_juego(self, nivel):
        """Inicializa el estado del juego para el nivel indicado y cambia el estado a JUGANDO."""
        cfg = CONFIGURACION_NIVELES[nivel]
        self.jp = {
            "nivel": nivel,
            "velocidad": cfg["velocidad"],
            "distancia": 0,
            "distancia_max": cfg["distancia"],
            "puntaje": 0,
            "vidas": 3,
            "jugador_y": float(SUELO_Y - 50),
            "jugador_vy": 0,
            "en_suelo": True,
            "tick_fotograma": 0,
            "fotograma_anim": 0,
            "obstaculos": [],
            "temporizador_obs": 0,
            "intervalo_obs": cfg["intervalo_obs"],
            "powerup": None,
            "temporizador_powerup": 0,
            "spawn_powerup_timer": random.randint(200, 400),
            "invencible": False,
            "temporizador_inv": 0,
            "anim_muerte": 0,
            "muerte_x": 0,
            "muerte_y": 0,
            "estado": "JUGANDO",  # JUGANDO, ANIM_MUERTE, GANADO, GAME_OVER
            "offset_suelo": 0,
            "offset_fondo": 0,
            "temporizador_flash": 0,
        }
        self.estado = "JUGANDO"
        self.particulas = []

    def _jugar(self):
        """Bucle principal del gameplay: procesa eventos, física, colisiones y dibuja la escena."""
        jp = self.jp
        cfg = CONFIGURACION_NIVELES[jp["nivel"]]
        eventos = pygame.event.get()
        for evento in eventos:
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self.estado = "SELECCION_NIVEL"
                    return
                if jp["estado"] == "JUGANDO":
                    if (evento.key == pygame.K_SPACE or evento.key == pygame.K_UP) and jp["en_suelo"]:
                        jp["jugador_vy"] = FUERZA_SALTO
                        jp["en_suelo"] = False
                        self._reproducir("salto")
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if jp["estado"] in ("GANADO", "GAME_OVER"):
                    self.estado = "SELECCION_NIVEL"
                    return

        if jp["estado"] == "JUGANDO":
            jp["tick_fotograma"] += 1
            jp["distancia"] += jp["velocidad"] / 10
            jp["puntaje"] = int(jp["distancia"] * jp["nivel"])
            jp["offset_fondo"] = (jp["offset_fondo"] + jp["velocidad"] * 0.3) % ANCHO
            jp["offset_suelo"] = (jp["offset_suelo"] + jp["velocidad"]) % ANCHO

            # Física del jugador
            jp["jugador_vy"] += GRAVEDAD
            jp["jugador_y"] += jp["jugador_vy"]
            if jp["jugador_y"] >= SUELO_Y - 50:
                jp["jugador_y"] = SUELO_Y - 50
                jp["jugador_vy"] = 0
                jp["en_suelo"] = True

            # Fotograma de animación
            if jp["en_suelo"]:
                jp["fotograma_anim"] = (jp["tick_fotograma"] // 6) % len(self.jugador_correr)

            # Invencibilidad
            if jp["invencible"]:
                jp["temporizador_inv"] -= 1
                if jp["temporizador_inv"] <= 0:
                    jp["invencible"] = False

            # Generar obstáculos
            jp["temporizador_obs"] += 1
            if jp["temporizador_obs"] >= jp["intervalo_obs"]:
                jp["temporizador_obs"] = 0
                tipo_obs, img_obs = random.choice(self.tipos_obstaculos)
                jp["obstaculos"].append({
                    "x": ANCHO + 20,
                    "img": img_obs,
                    "tipo": tipo_obs,
                    "ancho": img_obs.get_width(),
                    "alto": img_obs.get_height()
                })

            # Mover obstáculos
            nuevos_obs = []
            for obs in jp["obstaculos"]:
                obs["x"] -= jp["velocidad"]
                if obs["x"] + obs["ancho"] > 0:
                    nuevos_obs.append(obs)
            jp["obstaculos"] = nuevos_obs

            # Generar power-up
            jp["spawn_powerup_timer"] -= 1
            if jp["spawn_powerup_timer"] <= 0 and jp["powerup"] is None:
                jp["powerup"] = {"x": ANCHO + 20, "y": SUELO_Y - 90}
                jp["spawn_powerup_timer"] = random.randint(300, 600)

            # Mover power-up
            if jp["powerup"]:
                jp["powerup"]["x"] -= jp["velocidad"]
                if jp["powerup"]["x"] < -40:
                    jp["powerup"] = None

            # Rectángulo del jugador
            px = JUGADOR_X
            py = int(jp["jugador_y"])
            rect_jugador = pygame.Rect(px + 6, py, 28, 48)

            # Colisión con power-up
            if jp["powerup"]:
                rect_pw = pygame.Rect(jp["powerup"]["x"], jp["powerup"]["y"], 32, 32)
                if rect_jugador.colliderect(rect_pw):
                    jp["invencible"] = True
                    jp["temporizador_inv"] = 180
                    jp["powerup"] = None
                    self._reproducir("powerup")
                    self._crear_particulas(px, py, COLORES["dorado"], 20)

            # Colisión con obstáculos
            for obs in jp["obstaculos"]:
                rect_obs = pygame.Rect(obs["x"] + 4, SUELO_Y - obs["alto"] + 2, obs["ancho"] - 8, obs["alto"] - 4)
                if rect_jugador.colliderect(rect_obs):
                    if jp["invencible"]:
                        self._crear_particulas(obs["x"] + obs["ancho"]//2, SUELO_Y - obs["alto"]//2, COLORES["rojo"], 15)
                        jp["obstaculos"].remove(obs)
                        break
                    else:
                        jp["vidas"] -= 1
                        jp["temporizador_flash"] = 30
                        self._reproducir("morir")
                        self._crear_particulas(px, py, COLORES["rojo"], 20)
                        obs["x"] = -200
                        if jp["vidas"] <= 0:
                            jp["estado"] = "GAME_OVER"
                        break

            if jp["temporizador_flash"] > 0:
                jp["temporizador_flash"] -= 1

            # Condición de victoria
            if jp["distancia"] >= jp["distancia_max"]:
                jp["estado"] = "GANADO"
                self._reproducir("ganar")
                self._ganar_nivel()

        # ── DIBUJO ──
        self.pantalla.blit(self.fondo, (0, 0))

        self.pantalla.blit(self.tile_suelo, (-jp["offset_suelo"], SUELO_Y - 2))
        self.pantalla.blit(self.tile_suelo, (ANCHO - jp["offset_suelo"], SUELO_Y - 2))

        if jp["powerup"]:
            rebote = math.sin(jp["tick_fotograma"] * 0.1) * 5
            pw = self.img_powerup
            if jp["tick_fotograma"] % 4 < 2:
                brillo = pygame.Surface((pw.get_width()+8, pw.get_height()+8), pygame.SRCALPHA)
                pygame.draw.ellipse(brillo, (255, 220, 50, 80), brillo.get_rect())
                self.pantalla.blit(brillo, (jp["powerup"]["x"]-4, jp["powerup"]["y"] + rebote - 4))
            self.pantalla.blit(pw, (jp["powerup"]["x"], jp["powerup"]["y"] + rebote))

        for obs in jp["obstaculos"]:
            self.pantalla.blit(obs["img"], (obs["x"], SUELO_Y - obs["alto"]))

        px = JUGADOR_X
        py = int(jp["jugador_y"])
        flash_inv = jp["invencible"] and (jp["tick_fotograma"] % 4 < 2)
        if flash_inv:
            fotogramas = self.jugador_inv
            if jp["en_suelo"]:
                img = fotogramas[jp["fotograma_anim"] % len(fotogramas)]
            else:
                img = fotogramas[0]
            self.pantalla.blit(img, (px - 5, py - 5))
        else:
            if not jp["en_suelo"]:
                img = self.jugador_salto_img
            else:
                img = self.jugador_correr[jp["fotograma_anim"] % len(self.jugador_correr)]
            if jp["temporizador_flash"] > 0 and jp["temporizador_flash"] % 4 < 2:
                pass
            else:
                self.pantalla.blit(img, (px, py))

        if jp["invencible"]:
            ancho_barra = int((jp["temporizador_inv"] / 180) * 120)
            pygame.draw.rect(self.pantalla, COLORES["dorado"], (px - 40, py - 10, ancho_barra, 6), border_radius=3)
            pygame.draw.rect(self.pantalla, COLORES["gris_oscuro"], (px - 40, py - 10, 120, 6), 1, border_radius=3)

        self._actualizar_particulas()
        self._dibujar_hud(jp)

        if jp["estado"] == "GANADO":
            self._dibujar_overlay("¡NIVEL COMPLETADO!", COLORES["verde"],
                                  f"Score: {jp['puntaje']}  |  Clic para continuar")
        elif jp["estado"] == "GAME_OVER":
            self._dibujar_overlay("GAME OVER", COLORES["rojo"],
                                  "Clic para volver al menú de niveles")

    def _dibujar_hud(self, jp):
        """Dibuja el HUD: vidas, puntaje, barra de progreso, nivel y estado de invencibilidad."""
        barra_sup = pygame.Surface((ANCHO, 44), pygame.SRCALPHA)
        barra_sup.fill((0, 0, 0, 140))
        self.pantalla.blit(barra_sup, (0, 0))

        for i in range(3):
            color_vida = COLORES["verde"] if i < jp["vidas"] else COLORES["gris_oscuro"]
            pygame.draw.circle(self.pantalla, color_vida, (18 + i * 22, 22), 8)
            pygame.draw.circle(self.pantalla, COLORES["blanco"] if i < jp["vidas"] else COLORES["gris"],
                               (18 + i * 22, 22), 8, 1)

        self._texto(f"SCORE: {jp['puntaje']}", self.fuente_pequena, COLORES["blanco"], 180, 22)

        progreso = min(1.0, jp["distancia"] / jp["distancia_max"])
        bx_barra, by_barra, ancho_barra, alto_barra = 300, 13, 250, 18
        pygame.draw.rect(self.pantalla, COLORES["gris_oscuro"], (bx_barra, by_barra, ancho_barra, alto_barra), border_radius=4)
        pygame.draw.rect(self.pantalla, COLORES["acento"], (bx_barra, by_barra, int(ancho_barra * progreso), alto_barra), border_radius=4)
        pygame.draw.rect(self.pantalla, COLORES["borde_panel"], (bx_barra, by_barra, ancho_barra, alto_barra), 1, border_radius=4)
        texto_dist = f"{int(jp['distancia'])}m / {jp['distancia_max']}m"
        self._texto(texto_dist, self.fuente_pequena, COLORES["blanco"], bx_barra + ancho_barra//2, by_barra + alto_barra//2)

        self._texto(f"NIV.{jp['nivel']}  {self.usuario_actual}", self.fuente_pequena, COLORES["gris"],
                    ANCHO - 120, 22)

        if jp["invencible"]:
            t = (jp["tick_fotograma"] // 6) % 2
            color_inv = COLORES["dorado"] if t == 0 else COLORES["blanco"]
            self._texto("⚡ INVENCIBLE", self.fuente_pequena, color_inv, ANCHO//2, 60)

    def _dibujar_overlay(self, titulo, color_titulo, subtitulo):
        """Dibuja una pantalla semitransparente de victoria o game over con título y subtítulo."""
        superficie = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        superficie.fill((0, 0, 0, 170))
        self.pantalla.blit(superficie, (0, 0))
        self._texto(titulo, self.fuente_titulo, color_titulo, ANCHO//2, ALTO//2 - 40)
        self._texto(subtitulo, self.fuente_mediana, COLORES["blanco"], ANCHO//2, ALTO//2 + 20)

    def _ganar_nivel(self):
        """Guarda el puntaje si es récord personal y desbloquea el siguiente nivel."""
        nivel = self.jp["nivel"]
        puntaje = self.jp["puntaje"]
        datos_usuario = self.usuarios.get(self.usuario_actual) or default_user_data()
        clave_puntaje = f"level{nivel}_score"
        if puntaje > datos_usuario.get(clave_puntaje, 0):
            datos_usuario[clave_puntaje] = puntaje
        if nivel < 3:
            datos_usuario["levels_unlocked"] = max(datos_usuario.get("levels_unlocked", 1), nivel + 1)
        self.usuarios.insert(self.usuario_actual, datos_usuario)
        self.usuarios.save_to_file(ARCHIVO_GUARDADO)

    # ─── ESTADO: LEADERBOARD ──────────────────────────────────────────────────
    def _leaderboard(self):
        """Muestra todos los usuarios ordenados por puntaje total acumulado en los tres niveles."""
        self._dibujar_fondo()
        self._dibujar_panel((50, 50, ANCHO - 100, ALTO - 100))
        self._texto("LEADERBOARD", self.fuente_grande, COLORES["blanco"], ANCHO//2, 90)

        todos_usuarios = self.usuarios.get_all_users()
        con_puntaje = []
        for nombre, datos in todos_usuarios:
            total = datos.get("level1_score", 0) + datos.get("level2_score", 0) + datos.get("level3_score", 0)
            con_puntaje.append((nombre, datos, total))
        con_puntaje.sort(key=lambda x: -x[2])

        hx = 80
        self._texto("Pos",     self.fuente_pequena, COLORES["blanco"], hx + 40,  135, centrado=True)
        self._texto("Usuario", self.fuente_pequena, COLORES["blanco"], hx + 157, 135, centrado=True)
        self._texto("Niv1",    self.fuente_pequena, COLORES["blanco"], hx + 290, 135, centrado=True)
        self._texto("Niv2",    self.fuente_pequena, COLORES["blanco"], hx + 370, 135, centrado=True)
        self._texto("Niv3",    self.fuente_pequena, COLORES["blanco"], hx + 450, 135, centrado=True)
        self._texto("Total",   self.fuente_pequena, COLORES["blanco"], hx + 535, 135, centrado=True)
        pygame.draw.line(self.pantalla, COLORES["borde_panel"], (80, 150), (ANCHO-80, 150), 1)

        for i, (nombre, datos, total) in enumerate(con_puntaje[:12]):
            y = 165 + i * 35
            color_fila = COLORES["dorado"] if i == 0 else (COLORES["acento"] if i < 3 else COLORES["blanco"])
            if nombre == self.usuario_actual:
                resaltado = pygame.Surface((ANCHO-160, 26), pygame.SRCALPHA)
                resaltado.fill((60, 100, 180, 60))
                self.pantalla.blit(resaltado, (80, y - 8))
            self._texto(f"#{i+1}",                          self.fuente_pequena, color_fila,         hx + 40,  y, centrado=True)
            self._texto(nombre[:16],                         self.fuente_pequena, color_fila,         hx + 157, y, centrado=True)
            self._texto(str(datos.get("level1_score", 0)),   self.fuente_pequena, COLORES["blanco"],    hx + 290, y, centrado=True)
            self._texto(str(datos.get("level2_score", 0)),   self.fuente_pequena, COLORES["blanco"],    hx + 370, y, centrado=True)
            self._texto(str(datos.get("level3_score", 0)),   self.fuente_pequena, COLORES["blanco"],    hx + 450, y, centrado=True)
            self._texto(str(total),                          self.fuente_pequena, color_fila,         hx + 535, y, centrado=True)

        if not con_puntaje:
            self._texto("No hay usuarios registrados aún.", self.fuente_mediana, COLORES["gris"], ANCHO//2, 280)

        mx, my = pygame.mouse.get_pos()
        rect_volver = (ANCHO//2 - 80, ALTO - 80, 160, 40)
        hover_volver = rect_volver[0] <= mx <= rect_volver[0]+rect_volver[2] and rect_volver[1] <= my <= rect_volver[1]+rect_volver[3]
        self._dibujar_boton("< VOLVER", rect_volver, hover=hover_volver)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                self.estado = "MENU"
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if hover_volver:
                    self._reproducir("elegir")
                    self.estado = "MENU"

    # ─── ESTADO: AJUSTES ──────────────────────────────────────────────────────
    def _ajustes(self):
        """Renderiza la pantalla de ajustes: volumen, renombrar usuario, eliminar cuenta e info de la tabla hash."""
        self._dibujar_fondo()
        self._dibujar_panel((80, 60, ANCHO - 160, ALTO - 120))
        self._texto("SETTINGS", self.fuente_grande, COLORES["blanco"], ANCHO//2, 100)

        mx, my = pygame.mouse.get_pos()

        self._texto("VOLUMEN", self.fuente_pequena, COLORES["blanco"], 130, 148, centrado=False)
        rect_slider = (130, 170, 400, 22)
        pygame.draw.rect(self.pantalla, COLORES["gris_oscuro"], rect_slider, border_radius=6)
        ancho_relleno = int(self.volumen_ajustes / 100 * 400)
        pygame.draw.rect(self.pantalla, COLORES["rojo"], (130, 170, ancho_relleno, 22), border_radius=6)
        pygame.draw.rect(self.pantalla, (255, 255, 255), rect_slider, 2, border_radius=6)
        x_perilla = 130 + ancho_relleno
        pygame.draw.circle(self.pantalla, COLORES["blanco"], (x_perilla, 181), 11)
        self._texto(f"{self.volumen_ajustes}%", self.fuente_pequena, COLORES["blanco"], 555, 175, centrado=False)

        
        
        if pygame.mouse.get_pressed()[0]:
            if 130 <= mx <= 530 and 155 <= my <= 195:
                self.volumen_ajustes = int((mx - 130) / 400 * 100)
                self.volumen_ajustes = max(0, min(100, self.volumen_ajustes))
                if hasattr(self, '_musica') and self._musica:
                    self._musica.set_volume(self.volumen_ajustes / 100)
                

        base_y = 230
        sesion_activa = self.usuario_actual is not None

        if sesion_activa:
            self._texto(f"Usuario activo:  {self.usuario_actual}", self.fuente_mediana, COLORES["blanco"], 130, base_y, centrado=False)
            datos_usuario = self.usuarios.get(self.usuario_actual) or default_user_data()
            self._texto(f"Niveles desbloqueados: {datos_usuario.get('levels_unlocked', 1)}", self.fuente_pequena, COLORES["blanco"], 130, base_y + 30, centrado=False)
        else:
            self._texto("Sin sesión activa", self.fuente_mediana, COLORES["blanco"], 130, base_y, centrado=False)

        rect_renombrar = (130, base_y + 70, 200, 42)
        rect_eliminar  = (350, base_y + 70, 200, 42)
        rect_volver    = (ANCHO//2 - 80, ALTO - 60, 160, 40)

        hover_renombrar = rect_renombrar[0] <= mx <= rect_renombrar[0]+rect_renombrar[2] and rect_renombrar[1] <= my <= rect_renombrar[1]+rect_renombrar[3]
        hover_eliminar  = rect_eliminar[0]  <= mx <= rect_eliminar[0]+rect_eliminar[2]   and rect_eliminar[1]  <= my <= rect_eliminar[1]+rect_eliminar[3]
        hover_volver    = rect_volver[0]    <= mx <= rect_volver[0]+rect_volver[2]       and rect_volver[1]    <= my <= rect_volver[1]+rect_volver[3]

        self._dibujar_boton("ACTUALIZAR USUARIO", rect_renombrar, hover=hover_renombrar, bloqueado=not sesion_activa, fuente=self.fuente_pequena)
        self._dibujar_boton("ELIMINAR USUARIO",   rect_eliminar,  hover=hover_eliminar,  bloqueado=not sesion_activa, fuente=self.fuente_pequena)

        if self.modo_entrada_ajustes == "renombrar":
            self._texto("Nuevo nombre:", self.fuente_pequena, COLORES["blanco"], 130, base_y + 130, centrado=False)
            rect_entrada = (130, base_y + 145, 280, 40)
            self._dibujar_entrada("", self.nombre_nuevo_ajustes, rect_entrada, activo=True)
            rect_confirmar = (425, base_y + 160, 100, 40)
            hover_confirmar = rect_confirmar[0] <= mx <= rect_confirmar[0]+rect_confirmar[2] and rect_confirmar[1] <= my <= rect_confirmar[1]+rect_confirmar[3]
            self._dibujar_boton("OK", rect_confirmar, hover=hover_confirmar, fuente=self.fuente_pequena)
            rect_cancelar = (540, base_y + 160, 80, 40)
            hover_cancelar = rect_cancelar[0] <= mx <= rect_cancelar[0]+rect_cancelar[2] and rect_cancelar[1] <= my <= rect_cancelar[1]+rect_cancelar[3]
            self._dibujar_boton("X", rect_cancelar, hover=hover_cancelar, fuente=self.fuente_pequena)

        debug_y = base_y + 200
        self._dibujar_panel((130, debug_y, 500, 70), alfa=140)
        self._texto("[HASH TABLE] Estado interno", self.fuente_pequena, COLORES["blanco"], 140, debug_y + 10, centrado=False)
        self._texto(f"Size: {self.usuarios.size}  |  Capacity: {self.usuarios.capacity}  |  Load: {self.usuarios.size/max(1,self.usuarios.capacity):.2f}  |  Rehash at: {int(self.usuarios.capacity * 0.7)}",
                    self.fuente_pequena, COLORES["blanco"], 140, debug_y + 38, centrado=False)

        self._dibujar_boton("< VOLVER", rect_volver, hover=hover_volver)
        self._tick_mensaje()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self._salir()
            if evento.type == pygame.KEYDOWN:
                if self.modo_entrada_ajustes == "renombrar":
                    if evento.key == pygame.K_RETURN:
                        self._hacer_renombrar()
                    elif evento.key == pygame.K_ESCAPE:
                        self.modo_entrada_ajustes = None
                        self.nombre_nuevo_ajustes = ""
                    elif evento.key == pygame.K_BACKSPACE:
                        self.nombre_nuevo_ajustes = self.nombre_nuevo_ajustes[:-1]
                    elif len(self.nombre_nuevo_ajustes) < 18:
                        self.nombre_nuevo_ajustes += evento.unicode
                elif evento.key == pygame.K_ESCAPE:
                    self.estado = "MENU"
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if hover_volver:
                    self._reproducir("elegir")
                    self.estado = "MENU"
                if hover_renombrar and sesion_activa:
                    self._reproducir("elegir")
                    self.modo_entrada_ajustes = "renombrar"
                    self.nombre_nuevo_ajustes = ""
                if hover_eliminar and sesion_activa:
                    self._reproducir("elegir")
                    self._hacer_eliminar()
                if self.modo_entrada_ajustes == "renombrar":
                    rect_confirmar = (425, base_y + 160, 100, 40)
                    rect_cancelar  = (540, base_y + 160, 80,  40)
                    if rect_confirmar[0] <= mx <= rect_confirmar[0]+rect_confirmar[2] and rect_confirmar[1] <= my <= rect_confirmar[1]+rect_confirmar[3]:
                        self._hacer_renombrar()
                    if rect_cancelar[0] <= mx <= rect_cancelar[0]+rect_cancelar[2] and rect_cancelar[1] <= my <= rect_cancelar[1]+rect_cancelar[3]:
                        self.modo_entrada_ajustes = None
                        self.nombre_nuevo_ajustes = ""

    def _verificar_clic(self, rect, mx, my):
        """Retorna True si las coordenadas del mouse están dentro del rect dado."""
        return rect[0] <= mx <= rect[0]+rect[2] and rect[1] <= my <= rect[1]+rect[3]

    def _hacer_renombrar(self):
        """Valida y ejecuta el cambio de nombre del usuario actual en la tabla hash."""
        nombre_nuevo = self.nombre_nuevo_ajustes.strip()
        if not nombre_nuevo:
            self._mostrar_mensaje("Nombre vacío.", COLORES["rojo"])
            return
        if self.usuarios.user_exists(nombre_nuevo):
            self._mostrar_mensaje(f"'{nombre_nuevo}' ya existe.", COLORES["rojo"])
            return
        nombre_anterior = self.usuario_actual
        exito = self.usuarios.update_username(nombre_anterior, nombre_nuevo)
        if exito:
            self.usuario_actual = nombre_nuevo
            self.usuarios.save_to_file(ARCHIVO_GUARDADO)
            self._mostrar_mensaje(f"Renombrado a '{nombre_nuevo}'.", COLORES["verde"])
            print(f"[HASH TABLE] Renamed '{nombre_anterior}' -> '{nombre_nuevo}'")
        else:
            self._mostrar_mensaje("Error al renombrar.", COLORES["rojo"])
        self.modo_entrada_ajustes = None
        self.nombre_nuevo_ajustes = ""

    def _hacer_eliminar(self):
        """Elimina el usuario actual de la tabla hash, guarda y regresa al menú principal."""
        nombre = self.usuario_actual
        self.usuarios.delete(nombre)
        self.usuarios.save_to_file(ARCHIVO_GUARDADO)
        self.usuario_actual = None
        self._mostrar_mensaje(f"Usuario '{nombre}' eliminado.", COLORES["rojo"])
        print(f"[HASH TABLE] Deleted '{nombre}'")
        self.estado = "MENU"

    # ─── BUCLE PRINCIPAL ──────────────────────────────────────────────────────

    async def ejecutar(self):
        """Bucle principal del juego. Despacha el estado actual a su método correspondiente."""
        # Cargar música con pygame.mixer.Sound (más compatible con pygbag/WebAssembly)
        try:
            self._musica = pygame.mixer.Sound(self._ruta_musica)
            self._musica.set_volume(0.5)
            self._musica.play(-1)
            print("[MUSICA] Sonando")
        except Exception as e:
            print(f"[MUSICA] Error cargando música: {e}")
            self._musica = None

        while True:
            self.reloj.tick(FPS)
            if self.estado == "MENU":
                self._menu()
            elif self.estado == "NUEVO_USUARIO":
                self._nuevo_usuario()
            elif self.estado == "CARGAR_USUARIO":
                self._cargar_usuario()
            elif self.estado == "SELECCION_NIVEL":
                self._seleccion_nivel()
            elif self.estado == "JUGANDO":
                self._jugar()
            elif self.estado == "LEADERBOARD":
                self._leaderboard()
            elif self.estado == "AJUSTES":
                self._ajustes()

            pygame.display.flip()
            await asyncio.sleep(0)

    def _salir(self):
        self.usuarios.save_to_file(ARCHIVO_GUARDADO)
        pygame.quit()

if __name__ == "__main__":
    juego = JuegoJumper()
    asyncio.run(juego.ejecutar())