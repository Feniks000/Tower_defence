from time import time as global_time

from pygame.constants import *

from enemy import Enemy
from gui import *
from other import Vector
from other import distance, distance_to_vector
from turrets import TOWERS, prototype

STATUSES = dict()
buffer = open('CONSTS', 'r')
for key, val in map(lambda x: (x.split()[0], int(x.split()[1])), buffer.readlines()):
    STATUSES[key] = val
buffer.close()
del buffer, key, val


class GameMap:
    COSTS = {'InfernoTower': 20}
    x_size = 0
    y_size = 0
    line_width = 25
    game_map = list()
    base = None
    base_size = None
    background = pygame.image.load('images/background_v4.jpg')

    def __init__(self, path_to_map):
        file = open(path_to_map, 'r').readlines()
        self.x_size, self.y_size = map(int, file[0].split()[:-1])
        self.base_size = tuple(map(int, file[1].split()))
        file = tuple(map(lambda x: tuple(map(int, x.split())), file[2:]))
        self.game_map = [Vector(*file[i], *file[i + 1]) for i in range(len(file) - 1)]
        print(file)

    def get_map(self):
        return self.game_map

    def update(self, screen, base_hp):
        screen_width, screen_height = screen.get_width(), screen.get_height()
        screen.blit(pygame.transform.scale(self.background, (screen_width, screen_height)), (0, 0))
        for vec in self.game_map:
            pygame.draw.line(screen, pygame.Color(255, 0, 0), vec.begin(), vec.end(), self.line_width * 2)
        if self.base is not None:
            screen.blit(pygame.transform.scale(self.base, self.base_size[:2]), (self.base_size[2:]))
        else:
            pygame.draw.rect(screen, pygame.Color(255, 255, 255), pygame.Rect(*self.base_size))
            font = pygame.font.SysFont('Comic Sans MS', 32)
            text = font.render(str(base_hp), 1, pygame.Color(0, 100, 0))
            text_h = text.get_height()
            screen.blit(text, (self.base_size[0] + 5, self.base_size[1] + text_h))


class Game:
    money = 30
    COSTS = {'InfernoTower': 20}
    mouse_button_pressed = False
    # id
    focus_on = None
    time = 20
    # next id of in-game objects
    enemy_id = 0
    turrets_id = 0
    current_pos = (0, 0)
    fps = 60

    # objects case
    wave_size = 10
    wave_queue = dict()
    all_turrets = dict()
    all_enemies_on_map = dict()

    # waves params
    current_wave = 0  # for up enemy hp
    time_between_waves = 20 * 1000  # can be changed in settings

    # in-game objects
    menu = None
    game_map = None

    # flags
    pause_flag = False

    def __init__(self, difficult, path_to_map) -> None:
        self.difficult = difficult
        self.base_hp = 12 - difficult * 2
        self.game_map = GameMap(path_to_map)

    def load_map(self):
        pass

    def update(self, screen) -> None:
        pass

    def detected_enemy(self):
        a = distance
        busy = list()
        for enemy_id, enemy in self.all_enemies_on_map.items():
            for turret_id, turret in self.all_turrets.items():
                if distance(turret.pos(), enemy.pos()) < turret.range() and turret_id not in busy:
                    turret.set_target(enemy_id)
                    busy.append(turret_id)

    def move_enemies(self):
        for enemy_id, enemy in self.all_enemies_on_map.items():
            enemy.move()

    def update_enemies(self, screen):
        delete = []
        for enemy_id, enemy in self.all_enemies_on_map.items():
            status = enemy.update(screen)
            if status == STATUSES['ENEMY_STATUS_DIED']:
                delete.append(enemy_id)
                continue
            if status == STATUSES['ENEMY_STATUS_TO_GET_TO_BASE']:
                delete.append(enemy_id)
                self.base_hp -= 1
                continue
        for enemy_id in delete:
            self.money += self.all_enemies_on_map[enemy_id].wave
            del self.all_enemies_on_map[enemy_id]

    def update_turrets(self, screen):
        for turret_id, turret in self.all_turrets.items():
            turret.shoot(self.all_enemies_on_map)
            turret.update(screen, self.all_enemies_on_map)

    def next_wave_sender(self):
        self.current_wave += 1
        self.wave_queue[self.current_wave] = [0, self.wave_size]
        self.enemies_sender(self.current_wave)
        # pygame.time.set_timer(self.current_wave, ())

    def enemies_sender(self, ev_id):
        print('send')
        self.wave_queue[ev_id][1] -= 1
        self.all_enemies_on_map[self.enemy_id] = Enemy(self.game_map.get_map(), wave=ev_id, difficult=self.difficult)
        self.enemy_id = (self.enemy_id + 1) % 100000
        if self.wave_queue[ev_id][1] == 0:
            del self.wave_queue[ev_id]
            return
        self.wave_queue[ev_id][0] = global_time()

    def collision(self, pos, r, tower_type, screen) -> bool:
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        if self.money < self.COSTS[tower_type] or self.menu.rect is None:
            return True
        test = []
        for vec in self.game_map.get_map():
            test.append(distance_to_vector(pos, vec))
            if distance_to_vector(pos, vec) - self.game_map.line_width <= r:
                print(min(test))
                return True
        print(min(test))
        x, y = pos
        if x + r in range(self.menu.rect[0], self.menu.rect[2] + self.menu.rect[0] + 1) and \
                y + r in range(self.menu.rect[1], self.menu.rect[3] + self.menu.rect[1] + 1):
            return True
        if x not in range(r, screen_width - r + 1) or y not in range(r, screen_height - r + 1):
            return True
        if x + r in range(self.game_map.base_size[0], self.game_map.base_size[0] + self.game_map.base_size[2]) and \
                y + r in range(self.game_map.base_size[1], self.game_map.base_size[1] + self.game_map.base_size[3]):
            return True
        for _, turret in self.all_turrets.items():
            if distance(pos, (turret.x, turret.y)) <= r * 2:
                return True
        return False

    def build_tower(self, tower_type, pos):
        self.all_turrets[self.turrets_id] = TOWERS[tower_type](*pos)
        self.money -= self.COSTS[tower_type]
        self.turrets_id = (self.turrets_id + 1) % 100000

        pass

    def start(self, screen) -> (int, pygame.Surface):
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        # states and other params
        out_state = 0
        state = None  # this param store value from self.menu.event_handler()

        # id for time-depends events
        second = 30

        clock = pygame.time.Clock()
        pygame.time.set_timer(second, 1000)
        want_to_build_flag = False
        want_to_build_type = None
        self.menu = GameMenu()
        while out_state == 0 or out_state is None:  # main game-loop
            screen.fill(pygame.Color(255, 0, 0))
            state = None
            for event in pygame.event.get():  # event handler cycle
                # menu handle
                state = self.menu.event_handler(event)

                if event.type == QUIT:
                    return 8, screen

                if event.type == second:  # next wave event
                    pygame.time.set_timer(second, 1000)
                    self.time -= 1
                    if self.time == 0:
                        self.next_wave_sender()
                        self.time = 20
                    print('second passed')

                if event.type == KEYDOWN:  # hot-keys
                    if event.key == K_p:
                        self.pause_flag = True
                    if event.key == K_c:  # cheat button (add money)
                        self.money += 10000
                    if event.key == K_F4 and event.mod in (512, 256):
                        return 8, screen
                    if event.key == K_SPACE:
                        self.next_wave_sender()
                        self.time = 20
                        pygame.time.set_timer(second, 1000)

                if event.type == MOUSEMOTION:
                    self.current_pos = event.pos

                if event.type == MOUSEBUTTONDOWN:
                    self.mouse_button_pressed = True
                    if self.focus_on is not None:
                        self.all_turrets[self.focus_on].disable_trigger()
                    flag = True
                    for turret_id, turret in self.all_turrets.items():
                        if distance(event.pos, (turret.x, turret.y)) <= turret.r:
                            self.focus_on = turret_id
                            flag = False
                            break
                    if flag:
                        collision_x = event.pos[0] in range(self.menu.rect[0],
                                                            self.menu.rect[2] + self.menu.rect[0] + 1)
                        collision_y = event.pos[1] in range(self.menu.rect[1],
                                                            self.menu.rect[3] + self.menu.rect[1] + 1)
                        if not (collision_x and collision_y):
                            self.focus_on = None
                    if self.focus_on is not None:
                        self.all_turrets[self.focus_on].enable_trigger()

                if event.type == MOUSEBUTTONUP and self.mouse_button_pressed:
                    self.mouse_button_pressed = False

                    if want_to_build_flag:
                        if not self.collision(event.pos, 20, want_to_build_type, screen):
                            self.build_tower(want_to_build_type, event.pos)
                        want_to_build_flag = False
                        want_to_build_type = None

            wave_timers = tuple(self.wave_queue.items())
            for key, val in wave_timers:
                if global_time() - val[0] >= 1:
                    self.enemies_sender(key)

            self.move_enemies()
            self.detected_enemy()

            # handling state that returns a menu
            if state == 1:
                pygame.time.set_timer(second, 1000)
                self.time = 20
                self.next_wave_sender()

            if state == 2:
                print('built')
                want_to_build_flag = True
                want_to_build_type = 'InfernoTower'

            # screen update (DON'T CHANGE THE DRAWING ORDER)
            self.game_map.update(screen, self.base_hp)
            self.update_enemies(screen)
            self.update_turrets(screen)
            self.menu.update(screen, self.time, self.money)

            if want_to_build_flag:
                prototype(screen,
                          self.current_pos,
                          TOWERS[want_to_build_type].r,
                          TOWERS[want_to_build_type].r_of_attack,
                          self.collision(self.current_pos, TOWERS[want_to_build_type].r, want_to_build_type, screen))

            # fps wait and flip the display
            clock.tick(self.fps)
            pygame.display.flip()
            # end game-loop

        return out_state, screen
