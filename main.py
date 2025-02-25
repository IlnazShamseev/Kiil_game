import datetime
import math
import os
import random
import sqlite3
import sys
import time
from random import randint

import pygame
import pytmx

pygame.init()
pygame.display.set_caption('Kill the dino')


def way(files):
    # Возвращает полный путь до файла
    fullname = os.path.join("data", *files)
    if not os.path.isfile(fullname):
        print(f"Файл '{fullname}' не найден")
        import sys
        sys.exit()
    return fullname


def load_image(files, size=None, colorkey=None):
    # Возвращает изображение
    fullname = way(files)
    image = pygame.image.load(fullname)
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    if size is not None:
        image = pygame.transform.scale(image, size)
    return image


NOW = datetime.datetime.now().strftime("%D")
NAME_PLAYER = ""
SCORE = 0

CON = sqlite3.connect(way(("database.sql",)))
CURSOR = CON.cursor()
SCREEN_MAIN = pygame.display.set_mode(
    (1200, 800),
)

WIDTH, HEIGHT = SCREEN_MAIN.get_size()

FPS = 60
CLOCK = pygame.time.Clock()

pygame.mouse.set_visible(False)
MANUAL_CURSOR = load_image(("crosshair.png",), (30, 30), -1)


def mouse_get_pos():
    # Возвращает позицию мыши
    x, y = pygame.mouse.get_pos()
    w, h = MANUAL_CURSOR.get_size()
    return x - w // 2, y - h // 2


def get_font(name=None, size=30):
    # Возвращает шрифт по стилю и размеру
    return pygame.font.Font(None, size)


class Dino(pygame.sprite.Sprite):
    # Класс Dino является мобом
    image = [
        load_image(("hero", "DINO.png",), (32, 32), -1),
        pygame.transform.flip(load_image(("hero", "DINO.png",), (32, 32), -1), True, False)
    ]

    def __init__(self, x, y, v=100):
        super().__init__()
        self.image = Dino.image[0]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.v = v
        self.duration = "s"
        self.step = 0

    def update(self, *args):
        if self.rect.x >= args[0].rect.x:
            self.image = Dino.image[1]
        else:
            self.image = Dino.image[0
            ]


class Hero(pygame.sprite.Sprite):
    # Класс Hero является персонажем за которого мы управляем
    images = {
        "w": (
            load_image(("hero", "heroes_w0.png")),
            load_image(("hero", "heroes_w1.png")),
            load_image(("hero", "heroes_w2.png"))
        ),
        "a": (
            load_image(("hero", "heroes_a0.png")),
            load_image(("hero", "heroes_a1.png")),
            load_image(("hero", "heroes_a2.png"))
        ),
        "s": (
            load_image(("hero", "heroes_s0.png")),
            load_image(("hero", "heroes_s1.png")),
            load_image(("hero", "heroes_s2.png"))
        ),
        "d": (
            load_image(("hero", "heroes_d0.png")),
            load_image(("hero", "heroes_d1.png")),
            load_image(("hero", "heroes_d2.png"))
        ),
    }

    def __init__(self):
        super().__init__()
        self.image = Hero.images["s"][0]
        self.rect = self.image.get_rect()
        self.rect.x = (WIDTH - self.rect.x) // 2
        self.rect.y = (HEIGHT - self.rect.y) // 2
        self.FPS = 30

        self.v = 180
        self.duration = "s"
        self.step = 0

    def update(self, keyboard, mouse):
        w_key = keyboard[ord("w")]
        a_key = keyboard[ord("a")]
        s_key = keyboard[ord("s")]
        d_key = keyboard[ord("d")]

        if w_key ^ s_key or a_key ^ d_key:
            self.step = (self.step + 1) % self.FPS
            self.image = Hero.images[self.duration][self.step // (self.FPS // 2) + 1]

        if s_key and not w_key:
            if self.duration != "s":
                self.step = 0
                self.duration = "s"
        elif w_key and not s_key:
            if self.duration != "w":
                self.step = 0
                self.duration = "w"
        elif d_key and not a_key:
            if self.duration != "d":
                self.step = 0
                self.duration = "d"
        elif a_key and not d_key:
            if self.duration != "a":
                self.step = 0
                self.duration = "a"
        else:
            self.image = Hero.images[self.duration][0]
            self.step = 0


class Gun:
    # Класс Gun является оружием для устранения мобов
    def __init__(self, app):
        self.bullets = []
        self.loaded_cartridge = 6
        self.total_cartridge = 60

        self.blunders = 0

        self.app = app

    def shot(self, mouse):
        button_left, button_center, button_right = mouse.get_pressed()
        if not button_left or not self.loaded_cartridge:
            return
        self.loaded_cartridge -= 1
        x, y = mouse_get_pos()
        pos = self.app.left + WIDTH // 2 + self.app.hero.rect.width // 2, self.app.top + HEIGHT // 2 + self.app.hero.rect.height // 2
        v = 5
        x_vec = (x - (WIDTH // 2 + self.app.hero.rect.width // 2))
        y_vec = (y - (HEIGHT // 2 + self.app.hero.rect.height // 2))
        k = (v ** 2 / ((x_vec ** 2 + y_vec ** 2) / (FPS ** 2))) ** 0.5
        self.bullets.append((pos[0], pos[1], x_vec * k, y_vec * k))

    def recharge(self):
        if self.total_cartridge >= 6:
            self.total_cartridge += self.loaded_cartridge - 6
            self.loaded_cartridge = 6
        else:
            self.loaded_cartridge = self.total_cartridge
            self.total_cartridge = 0

    def update(self):
        global SCORE
        bullets = []

        for bullet in self.bullets:
            x_pos, y_pos, x_vec, y_vec = bullet
            x_pos += x_vec / FPS
            y_pos += y_vec / FPS

            dinos = []
            f = True
            for dino in self.app.dinos:
                if dino.rect.x <= x_pos <= dino.rect.x + dino.rect.width:
                    if dino.rect.y <= y_pos <= dino.rect.y + dino.rect.height:
                        if f:
                            SCORE += 1
                            f = False
                            continue
                dinos.append(dino)
            self.app.dinos = dinos

            if f:
                if 0 <= x_pos <= self.app.tile_size * self.app.width:
                    if 0 <= y_pos <= self.app.tile_size * self.app.height:
                        bullets.append(
                            (x_pos, y_pos, x_vec, y_vec)
                        )

        self.bullets = bullets

    def get_bullets(self):
        return self.bullets

    def info(self):
        return self.loaded_cartridge, self.total_cartridge


class Application:
    # Сама игра - основное приложение
    def __init__(self):
        self.map = pytmx.load_pygame(way(("maps", "map.tmx")))

        self.height = self.map.height
        self.width = self.map.width
        self.tile_size = self.map.tilewidth

        self.screen = pygame.Surface(size=(self.width * self.tile_size, self.height * self.tile_size))
        self.walls = [[0] * self.width for i in range(self.height)]

        self.creature_map(self.screen)

        self.hero = Hero()
        self.dinos = []
        self.gun = Gun(self)

        self.start_time = time.time()
        self.if_creature_dino = False
        self.if_game = True

        self.left = (self.tile_size * self.width - WIDTH) // 2
        self.top = (self.tile_size * self.width - HEIGHT) // 2

    def creature_map(self, screen):
        for k in range(7):
            for y in range(self.height):
                for x in range(self.width):
                    image = self.map.get_tile_image(x, y, k)
                    if image is not None:
                        if k:
                            self.walls[y][x] = 1
                        pygame.transform.scale(image,
                                               (self.tile_size, self.tile_size)
                                               )
                        screen.blit(image, (x * self.tile_size, y * self.tile_size))

    def render(self, screen):
        screen.blit(self.screen, (0, 0), (self.left, self.top, WIDTH, HEIGHT))
        screen.blit(self.hero.image, self.hero.rect)

        for dino in self.dinos:
            dino.update(self.hero)
            screen.blit(
                dino.image,
                (dino.rect.x - self.left, dino.rect.y - self.top, dino.rect.width, dino.rect.height)
            )

        for bullet in self.gun.get_bullets():
            x_pos, y_pos, _, _ = bullet
            if self.left <= x_pos <= self.left + WIDTH:
                pygame.draw.circle(
                    screen, "red", (x_pos - self.left, y_pos - self.top), 5
                )

        gun_info = self.gun.info()
        string_rendered = get_font(size=50).render(f"{gun_info[0]}//{gun_info[1]}", 1, pygame.Color("white"), )
        intro_rect = string_rendered.get_rect()
        intro_rect.top = 98
        intro_rect.x = 98
        SCREEN_MAIN.blit(string_rendered, intro_rect)

        gun_info = self.gun.info()
        string_rendered = get_font(size=50).render(f"{gun_info[0]}//{gun_info[1]}", 1, pygame.Color("black"), )
        intro_rect = string_rendered.get_rect()
        intro_rect.top = 100
        intro_rect.x = 100
        SCREEN_MAIN.blit(string_rendered, intro_rect)

    def move_hero(self, keyboard):
        w_key = keyboard[ord("w")]
        a_key = keyboard[ord("a")]
        s_key = keyboard[ord("s")]
        d_key = keyboard[ord("d")]

        if not (w_key ^ s_key or a_key ^ d_key):
            return

        pix = self.hero.v // FPS

        vec_width = 0
        vec_height = 0

        # 1
        if s_key and not w_key:
            if d_key and not a_key:
                pix = pix // (2 ** 0.5)
                vec_width += pix
            elif a_key and not d_key:
                pix = pix // (2 ** 0.5)
                vec_width -= pix
            vec_height += pix
        elif w_key and not s_key:
            if d_key and not a_key:
                pix = pix // (2 ** 0.5)
                vec_width += pix
            elif a_key and not d_key:
                pix = pix // (2 ** 0.5)
                vec_width -= pix
            vec_height -= pix
        elif d_key and not a_key:
            vec_width += pix
        elif a_key and not d_key:
            vec_width -= pix

        # 2
        if vec_width < 0:
            pos_x = int((self.left + WIDTH // 2) // self.tile_size)
            pos_y1 = int((self.top + HEIGHT // 2) // self.tile_size)
            pos_y2 = int(math.ceil((self.top + HEIGHT // 2 + self.hero.rect.height) / self.tile_size))

            for i in range(pos_y2 - pos_y1):
                if self.walls[pos_y1 + i][pos_x]:
                    break
            else:
                self.left += vec_width
        elif vec_width > 0:
            pos_x = int((self.left + WIDTH // 2 + self.hero.rect.width) // self.tile_size)
            pos_y1 = int((self.top + HEIGHT // 2) // self.tile_size)
            pos_y2 = int(math.ceil((self.top + HEIGHT // 2 + self.hero.rect.height) / self.tile_size))

            for i in range(pos_y2 - pos_y1):
                if self.walls[pos_y1 + i][pos_x]:
                    break
            else:
                self.left += vec_width

        if vec_height < 0:
            pos_y = int((self.top + HEIGHT // 2) // self.tile_size)
            pos_x1 = int((self.left + WIDTH // 2) // self.tile_size)
            pos_x2 = int((self.left + WIDTH // 2 + self.hero.rect.width) // self.tile_size)

            for i in range(pos_x2 - pos_x1):
                if self.walls[pos_y][pos_x1 + i]:
                    break
            else:
                self.top += vec_height
        elif vec_height > 0:
            pos_y = int((self.top + HEIGHT // 2 + self.hero.rect.height) // self.tile_size)
            pos_x1 = int((self.left + WIDTH // 2) // self.tile_size)
            pos_x2 = int((self.left + WIDTH // 2 + self.hero.rect.width) // self.tile_size)

            for i in range(pos_x2 - pos_x1):
                if self.walls[pos_y][pos_x1 + i]:
                    break
            else:
                self.top += vec_height

        self.left = min(max(self.left, -WIDTH // 2), self.tile_size * self.width - WIDTH // 2 - self.hero.rect.width)
        self.top = min(max(self.top, -HEIGHT // 2), self.tile_size * self.height - HEIGHT // 2 - self.hero.rect.height)

    def hero_alive(self):
        for dino in self.dinos:
            x_dino, y_dino = dino.rect.x, dino.rect.y
            w_dino, h_dino = dino.rect.width, dino.rect.height

            x_hero, y_hero = self.hero.rect.x + self.left, self.hero.rect.y + self.top
            w_hero, h_hero = self.hero.rect.width, self.hero.rect.height

            if x_hero <= x_dino <= x_hero + w_hero:
                if y_hero <= y_dino <= y_hero + h_hero:
                    self.if_game = False
                    return
                elif y_hero <= y_dino + h_dino <= y_hero + h_hero:
                    self.if_game = False
                    return
            elif x_hero <= x_dino + w_dino <= x_hero + w_hero:
                if y_hero <= y_dino <= y_hero + h_hero:
                    self.if_game = False
                    return
                elif y_hero <= y_dino + h_dino <= y_hero + h_hero:
                    self.if_game = False
                    return

    def shot(self, mouse):
        self.gun.shot(pygame.mouse)

    def create_dino(self):
        now_time = time.time()
        sec = round(now_time - self.start_time, 2)

        if 20 >= sec * 100 - int(sec) * 100 >= 0:
            if not self.if_creature_dino:
                self.if_creature_dino = True
                for i in range(int(now_time - self.start_time) // 20 + 1):
                    sector = random.randint(0, 2)
                    dino = Dino(0, 0)
                    if sector == 0:
                        dino.rect.x = 50
                        dino.rect.y = (self.tile_size * self.height - dino.rect.height) // 2 + randint(-50, 50)
                    elif sector == 1:
                        dino.rect.x = self.tile_size * self.width - dino.rect.width - 50
                        dino.rect.y = (self.tile_size * self.height - dino.rect.height) // 2 + randint(-50, 50)
                    else:
                        dino.rect.x = (self.tile_size * self.width - dino.rect.width) // 2 + randint(-50, 50)
                        dino.rect.y = self.tile_size * self.height - dino.rect.height - 50
                    self.dinos.append(dino)
        else:
            self.if_creature_dino = False

    def move_dinos(self):
        for dino in self.dinos:
            w = (self.left + self.hero.rect.x + self.hero.rect.width // 2) - (dino.rect.x + dino.rect.width // 2)
            h = (self.top + self.hero.rect.y + self.hero.rect.height // 2) - (dino.rect.y + dino.rect.height // 2)
            s = (w ** 2 + h ** 2) ** 0.5

            k = s / dino.v

            dino.rect.x += round(w / k / FPS)
            dino.rect.y += round(h / k / FPS)

    def recharge(self):
        self.gun.recharge()

    def update(self, keyboard, mouse):
        self.create_dino()
        self.hero_alive()
        self.hero.update(keyboard, mouse)
        self.move_hero(keyboard)
        self.move_dinos()
        self.gun.update()


def start_screen():
    # Начальный экран
    def print_on_display():
        text = [
            "Добро пожаловать",
            "Введите имя",
        ]

        font = get_font(size=50)
        text_coord = 50

        SCREEN_MAIN.fill("black")

        for line in text:
            string_rendered_white = font.render(line, 1, pygame.Color("white"))
            string_rendered_black = font.render(line, 1, pygame.Color("black"))

            rect_white = string_rendered_white.get_rect()
            rect_black = string_rendered_black.get_rect()
            text_coord += 50

            rect_white.top = text_coord
            rect_black.top = text_coord + 2

            rect_white.x = 50
            rect_black.x = 52

            text_coord += rect_white.height
            SCREEN_MAIN.blit(string_rendered_white, rect_white)
            SCREEN_MAIN.blit(string_rendered_black, rect_black)

        string_rendered_white = font.render(NAME_PLAYER, 1, pygame.Color("white"))
        string_rendered_black = font.render(NAME_PLAYER, 1, pygame.Color("black"))

        rect_white = string_rendered_white.get_rect()
        rect_black = string_rendered_black.get_rect()
        text_coord += 50

        rect_white.top = text_coord
        rect_black.top = text_coord + 2

        rect_white.x = 50
        rect_black.x = 52

        text_coord += rect_white.height
        SCREEN_MAIN.blit(string_rendered_white, rect_white)
        SCREEN_MAIN.blit(string_rendered_black, rect_black)

    global NAME_PLAYER
    print_on_display()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    if NAME_PLAYER:
                        NAME_PLAYER = NAME_PLAYER[:-1]
                elif 97 <= event.key <= 122 and len(NAME_PLAYER) < 8:
                    NAME_PLAYER += chr(event.key).upper()
                elif event.key == pygame.K_RETURN and NAME_PLAYER:
                    CURSOR.execute(
                        f'INSERT INTO LEADER_BOARD (NAME, DATE) VALUES ("{NAME_PLAYER}", "{NOW}")'
                    )
                    CON.commit()
                    return
                print_on_display()

        pygame.display.flip()
        CLOCK.tick(FPS)


def end_screen():
    # Конечный экран
    def print_on_display():
        text = [
            "Вы умерли",
            f"Выш счет : {SCORE}",
        ]

        font = get_font(size=50)
        text_coord = 50

        SCREEN_MAIN.fill("black")

        for line in text:
            string_rendered_white = font.render(line, 1, pygame.Color("white"))
            string_rendered_black = font.render(line, 1, pygame.Color("black"))

            rect_white = string_rendered_white.get_rect()
            rect_black = string_rendered_black.get_rect()
            text_coord += 50

            rect_white.top = text_coord
            rect_black.top = text_coord + 2

            rect_white.x = 50
            rect_black.x = 52

            text_coord += rect_white.height
            SCREEN_MAIN.blit(string_rendered_white, rect_white)
            SCREEN_MAIN.blit(string_rendered_black, rect_black)

        string_rendered_white = font.render(NAME_PLAYER, 1, pygame.Color("white"))
        string_rendered_black = font.render(NAME_PLAYER, 1, pygame.Color("black"))

        rect_white = string_rendered_white.get_rect()
        rect_black = string_rendered_black.get_rect()
        text_coord += 50

        rect_white.top = text_coord
        rect_black.top = text_coord + 2

        rect_white.x = 50
        rect_black.x = 52

        text_coord += rect_white.height
        SCREEN_MAIN.blit(string_rendered_white, rect_white)
        SCREEN_MAIN.blit(string_rendered_black, rect_black)

        text_coord = 50
        left = 500

        for i in sorted(map(lambda x: (x[0], int(x[1][1]) + int(x[1][0]) * 30 + (int(x[1][2]) - 25) * 30 * 365, x[2]),
                            map(lambda x: (x[1], x[2].split("/"), x[0]), CURSOR.execute("SELECT * FROM LEADER_BOARD"))),
                        reverse=True)[:5]:
            name = i[2]
            score = str(i[0])

            string_rendered_name_white = font.render(name, 1, pygame.Color("white"))
            string_rendered_name_black = font.render(name, 1, pygame.Color("black"))
            string_rendered_score_white = font.render(score, 1, pygame.Color("white"))
            string_rendered_score_black = font.render(score, 1, pygame.Color("black"))

            rect_name_white = string_rendered_name_white.get_rect()
            rect_name_black = string_rendered_name_black.get_rect()
            rect_score_white = string_rendered_score_white.get_rect()
            rect_score_black = string_rendered_score_black.get_rect()
            text_coord += 50

            rect_name_white.top = text_coord
            rect_name_black.top = text_coord + 2
            rect_score_white.top = text_coord
            rect_score_black.top = text_coord + 2

            rect_name_white.x = left + 50
            rect_name_black.x = left + 52
            rect_score_white.x = left
            rect_score_black.x = left + 2

            text_coord += rect_name_white.height
            SCREEN_MAIN.blit(string_rendered_name_white, rect_name_white)
            SCREEN_MAIN.blit(string_rendered_name_black, rect_name_black)
            SCREEN_MAIN.blit(string_rendered_score_white, rect_score_white)
            SCREEN_MAIN.blit(string_rendered_score_black, rect_score_black)

    global NAME_PLAYER

    q = CURSOR.execute(f"""SELECT SCORE FROM LEADER_BOARD WHERE NAME == '{NAME_PLAYER}'""")
    res = SCORE
    for i in q:
        res = max(int(i[0]), res)

    CURSOR.execute(f"""UPDATE LEADER_BOARD SET SCORE = {SCORE} WHERE NAME = '{NAME_PLAYER}'""")
    CON.commit()

    print_on_display()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        pygame.display.flip()
        CLOCK.tick(FPS)


start_screen()

GAME_MAIN = Application()

while GAME_MAIN.if_game:
    shot = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            GAME_MAIN.if_game = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            GAME_MAIN.shot(pygame.mouse)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                GAME_MAIN.recharge()

    SCREEN_MAIN.fill("black")

    GAME_MAIN.render(SCREEN_MAIN)
    GAME_MAIN.update(pygame.key.get_pressed(), pygame.mouse)

    mouse_pos = mouse_get_pos()
    mouse_size = MANUAL_CURSOR.get_size()

    SCREEN_MAIN.blit(MANUAL_CURSOR, (mouse_pos[0] - mouse_size[0], mouse_pos[1] - mouse_size[1]))

    CLOCK.tick(FPS)
    pygame.display.flip()

end_screen()
