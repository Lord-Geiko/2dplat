import pygame, sys, os, random, math
clock = pygame.time.Clock()

from pygame.locals import *
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init() # initiates pygame
pygame.mixer.set_num_channels(64)

pygame.display.set_caption('Above & Beyond')

WINDOW_SIZE = (800,600)

screen = pygame.display.set_mode(WINDOW_SIZE,0,32) # initiate the window

display = pygame.Surface((300,200)) # used as the surface for rendering, which is scaled

SPAWN_X, SPAWN_Y = 100, 100
MAX_HP = 100
player_hp = MAX_HP

moving_right = False
moving_left = False
player_vertical_momentum = 0
npc_vertical_momentum = 0
vertical_momentum = 0
air_timer = 0

#DEFINE THE HQ AND ITS DOOR
HEADQUARTER_X, HEADQUARTER_Y = 550, 105
HEADQUARTER_WIDTH, HEADQUARTER_HEIGHT = 64, 64 #ADJUST BASED ON YOUR ART
DOOR_WIDTH, DOOR_HEIGHT = 10, 10 # ADJUST BASED ON DOOR ART
DOOR_OFFSET_X, DOOR_OFFSET_Y = 18, 45 #ADJUST BASED ON DOOR POSITION IN ART

#CREATE RECTANGLES FOR THE HEADQUARTERS AND ITS DOORS
headquarter_rect = pygame.Rect(HEADQUARTER_X, HEADQUARTER_Y, HEADQUARTER_WIDTH, HEADQUARTER_HEIGHT)
door_rect = pygame.Rect(headquarter_rect.x + DOOR_OFFSET_X, headquarter_rect.y + DOOR_OFFSET_Y, DOOR_WIDTH, DOOR_HEIGHT)

true_scroll = [0,0]

CHUNK_SIZE = 8
NPC_SPEED = 1

BOUNCE_COOLDOWN = 30 #FRAMES
bounce_timer = 0
MUSHROOM_BOUNCE_STRENGTH = -15 #STRONGER UPWARDS BOUNCE

def generate_chunk(x,y):
    chunk_data = []
    for y_pos in range(CHUNK_SIZE):
        for x_pos in range(CHUNK_SIZE):
            target_x = x * CHUNK_SIZE + x_pos
            target_y = y * CHUNK_SIZE + y_pos
            tile_type = 0 # nothing
            if target_y > 10:
                tile_type = 2 # dirt
            elif target_y == 10:
                tile_type = 1 # grass
            elif target_y == 9:
                if random.randint(1,5) == 1:
                    tile_type = 3 # plant
            if tile_type != 0:
                chunk_data.append([[target_x,target_y],tile_type])
    return chunk_data


global animation_frames
animation_frames = {}

def load_animation(path,frame_durations):
    global animation_frames
    animation_name = path.split('/')[-1]
    animation_frame_data = []
    n = 0
    for frame in frame_durations:
        animation_frame_id = animation_name + '_' + str(n)
        img_loc = path + '/' + animation_frame_id + '.png'
        # player_animations/idle/idle_0.png
        animation_image = pygame.image.load(img_loc).convert_alpha()
        animation_image.set_colorkey((255,255,255))
        animation_frames[animation_frame_id] = animation_image.copy()
        for i in range(frame):
            animation_frame_data.append(animation_frame_id)
        n += 1
    return animation_frame_data

def change_action(action_var,frame,new_value):
    if action_var != new_value:
        action_var = new_value
        frame = 0
    return action_var,frame

animation_database = {}

animation_database['run'] = load_animation('player_animations/run',[7,7])
animation_database['idle'] = load_animation('player_animations/idle',[7,7,40])
animation_database['npc'] = load_animation('player_animations/npc', [7, 7, 40])
animation_database['shroom'] = load_animation('player_animations/shroom', [7, 7, 50])
animation_database['pixie'] = load_animation('player_animations/pixie', [7,7])
animation_database['headquarter'] = load_animation('player_animations/headquarter', [7])
animation_database['tree'] = load_animation('player_animations/tree', [7])

game_map = {}

grass_img = pygame.image.load('grass.png')
dirt_img = pygame.image.load('dirt.png')
plant_img = pygame.image.load('plant.png').convert()
plant_img.set_colorkey((255,255,255))

tile_index = {1:grass_img,
              2:dirt_img,
              3:plant_img
              }

jump_sound = pygame.mixer.Sound('jump.wav')
grass_sounds = [pygame.mixer.Sound('grass_0.wav'),pygame.mixer.Sound('grass_1.wav')]
grass_sounds[0].set_volume(0.2)
grass_sounds[1].set_volume(0.2)

pygame.mixer.music.load('music.wav')
pygame.mixer.music.play(-1)

player_action = 'idle'
player_frame = 0
player_flip = False

shroom_action = 'shroom'
shroom_frame = 0
shroom_flip = False

npc_action = 'npc'
npc_frame = 0
npc_flip = False

pixie_action = 'pixie'
pixie_frame = 0
pixie_flip = False

headquarter_action = 'headquarter'
headquarter_frame = 0
headquarter_flip = False

tree_action = 'tree'
tree_frame = 0
tree_flip = False

tree_rect = pygame.Rect(-550, 105, 5, 13)

headquarter_rect = pygame.Rect(550, 105, 5, 13)

pixie_rect = pygame.Rect(400, 145, 5, 13)

shroom_rect = pygame.Rect(55, 145, 5, 5)

npc_rect = pygame.Rect(85, 145, 5, 13)

grass_sound_timer = 0

player_rect = pygame.Rect(100,100,5,13)

background_objects = [[0.25,[120,10,70,400]],[0.25,[280,30,40,400]],[0.5,[30,40,40,400]],[0.5,[130,90,100,400]],[0.5,[300,80,120,400]]]

def collision_test(rect,tiles):
    hit_list = []
    for tile in tiles:
        if rect.colliderect(tile):
            hit_list.append(tile)
    return hit_list

def move(rect,movement,tiles):
    collision_types = {'top':False,'bottom':False,'right':False,'left':False}
    rect.x += movement[0]
    hit_list = collision_test(rect,tiles)
    for tile in hit_list:
        if movement[0] > 0:
            rect.right = tile.left
            collision_types['right'] = True
        elif movement[0] < 0:
            rect.left = tile.right
            collision_types['left'] = True
    rect.y += movement[1]
    hit_list = collision_test(rect,tiles)
    for tile in hit_list:
        if movement[1] > 0:
            rect.bottom = tile.top
            collision_types['bottom'] = True
        elif movement[1] < 0:
            rect.top = tile.bottom
            collision_types['top'] = True
    return rect, collision_types

def draw_hp_bar(surface, x, y, hp, max_hp):
    BAR_LENGTH = 50
    BAR_HEIGHT = 5
    fill = (hp / max_hp) * BAR_LENGTH
    bg_rect = pygame.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
    fill_rect = pygame.Rect(x, y, fill, BAR_HEIGHT)
    pygame.draw.rect(surface, (60, 60, 60), bg_rect)  # Dark grey background
    pygame.draw.rect(surface, (255, 0, 0), fill_rect)
    pygame.draw.rect(surface, (255, 255, 255), bg_rect, 1)

def check_shroom_collision(player, shroom):
    return player.colliderect(shroom)

while True: # game loop
    display.fill((146,244,255)) # clear screen by filling it with blue

     # Draw HP bar on the display surface
    draw_hp_bar(display, display.get_width() - 55, 5, player_hp, MAX_HP)

    #Update door position for if headquarter position changes
    door_rect.x = headquarter_rect.x + DOOR_OFFSET_X
    door_rect.y = headquarter_rect.y + DOOR_OFFSET_Y

    # Scale display to screen
    screen.blit(pygame.transform.scale(display, WINDOW_SIZE), (0, 0))
    
    if grass_sound_timer > 0:
        grass_sound_timer -= 1

    true_scroll[0] += (player_rect.x-true_scroll[0]-152)/20
    true_scroll[1] += (player_rect.y-true_scroll[1]-106)/20
    scroll = true_scroll.copy()
    scroll[0] = int(scroll[0])
    scroll[1] = int(scroll[1])

    pygame.draw.rect(display,(7,80,75),pygame.Rect(0,120,300,80))
    for background_object in background_objects:
        obj_rect = pygame.Rect(background_object[1][0]-scroll[0]*background_object[0],background_object[1][1]-scroll[1]*background_object[0],background_object[1][2],background_object[1][3])
        if background_object[0] == 0.5:
            pygame.draw.rect(display,(20,170,150),obj_rect)
        else:
            pygame.draw.rect(display,(15,76,73),obj_rect)

    tile_rects = []
    for y in range(3):
        for x in range(4):
            target_x = x - 1 + int(round(scroll[0]/(CHUNK_SIZE*16)))
            target_y = y - 1 + int(round(scroll[1]/(CHUNK_SIZE*16)))
            target_chunk = str(target_x) + ';' + str(target_y)
            if target_chunk not in game_map:
                game_map[target_chunk] = generate_chunk(target_x,target_y)
            for tile in game_map[target_chunk]:
                display.blit(tile_index[tile[1]],(tile[0][0]*16-scroll[0],tile[0][1]*16-scroll[1]))
                if tile[1] in [1,2]:
                    tile_rects.append(pygame.Rect(tile[0][0]*16,tile[0][1]*16,16,16))    

    player_movement = [0,0]
    if moving_right == True:
        player_movement[0] += 2
    if moving_left == True:
        player_movement[0] -= 2
    player_movement[1] += player_vertical_momentum
    player_vertical_momentum += 0.2
    if player_vertical_momentum > 3:
        player_vertical_momentum = 3

    if player_movement[0] == 0:
        player_action,player_frame = change_action(player_action,player_frame,'idle')
    if player_movement[0] > 0:
        player_flip = False
        player_action,player_frame = change_action(player_action,player_frame,'run')
    if player_movement[0] < 0:
        player_flip = True
        player_action,player_frame = change_action(player_action,player_frame,'run')
    
    #check for collision with shroom
    if check_shroom_collision(player_rect, shroom_rect) and bounce_timer == 0:
        if player_rect.bottom <= shroom_rect.top + 5: # allow a small margin for detection
            #bounce the player high into the sky
            player_vertical_momentum = MUSHROOM_BOUNCE_STRENGTH
            bounce_timer = BOUNCE_COOLDOWN
        #determine the direction to bounce
        if player_rect.centerx < shroom_rect.centerx:
            #player is left of shroom
            player_rect.x -= 200 #move player 2 tiles
            player_movement[0] = -5 # set horizontal movement to left
        else:
            #player is to the right
            player_rect.x += 200
            player_movement[0] = 5
    
    if bounce_timer > 0:
        bounce_timer -= 1
    
    if player_rect.x > npc_rect.x:
        npc_rect.x += NPC_SPEED
        npc_flip = False
    elif player_rect.x < npc_rect.x:
        npc_rect.x -= NPC_SPEED
        npc_flip = True

    if player_rect.y > npc_rect.y:
        npc_rect.y += NPC_SPEED
    elif player_rect.y < npc_rect.y:
        npc_rect.y -= NPC_SPEED

    # Ensure NPC stays within certain distance of player
    max_distance = 100
    dx = player_rect.x - npc_rect.x
    dy = player_rect.y - npc_rect.y
    distance = (dx**2 + dy**2)**0.5

    if distance > max_distance:
        angle = math.atan2(dy, dx)
        npc_rect.x += NPC_SPEED * math.cos(angle)
        npc_rect.y += NPC_SPEED * math.sin(angle)

    # Collision detection for NPC
    npc_movement = [0, 0]
    npc_movement[1] += npc_vertical_momentum
    npc_rect, npc_collisions = move(npc_rect, npc_movement, tile_rects)

    if npc_collisions['bottom']:
        npc_vertical_momentum = 0
    else:
        npc_vertical_momentum += 0.2
        if npc_vertical_momentum > 3:
            npc_vertical_momentum = 3

    # Update NPC animation
    npc_frame += 1
    if npc_frame >= len(animation_database[npc_action]):
        npc_frame = 0
    npc_img_id = animation_database[npc_action][npc_frame]
    npc_img = animation_frames[npc_img_id]
    display.blit(pygame.transform.flip(npc_img, npc_flip, False), (npc_rect.x-scroll[0], npc_rect.y-scroll[1]))

    player_rect,collisions = move(player_rect,player_movement,tile_rects)

    if collisions['bottom'] == True:
        air_timer = 0
        vertical_momentum = 0
        if player_movement[0] != 0:
            if grass_sound_timer == 0:
                grass_sound_timer = 30
                random.choice(grass_sounds).play()
    else:
        air_timer += 1

    if player_rect.colliderect(door_rect):
        #teleport player to spawn
        player_rect.x = SPAWN_X
        player_rect.y = SPAWN_Y
        player_vertical_momentum = 0

    npc_frame += 1
    if npc_frame >= len(animation_database[npc_action]):
        npc_frame = 0
    npc_img_id = animation_database[npc_action][npc_frame]
    npc_img = animation_frames[npc_img_id]
    display.blit(pygame.transform.flip(npc_img, npc_flip, False), (npc_rect.x-scroll[0], npc_rect.y-scroll[1]))

    shroom_frame += 1
    if shroom_frame >= len(animation_database[shroom_action]):
        shroom_frame = 0
    shroom_img_id = animation_database[shroom_action][shroom_frame]
    shroom_img = animation_frames[shroom_img_id]
    display.blit(pygame.transform.flip(shroom_img, shroom_flip, False), (shroom_rect.x-scroll[0], shroom_rect.y-scroll[1]))

    pixie_frame += 1
    if pixie_frame >= len(animation_database[pixie_action]):
        pixie_frame = 0
    pixie_img_id = animation_database[pixie_action][pixie_frame]
    pixie_img = animation_frames[pixie_img_id]
    display.blit(pygame.transform.flip(pixie_img, pixie_flip, False), (pixie_rect.x-scroll[0], pixie_rect.y-scroll[1]))

    headquarter_frame += 1
    if headquarter_frame >= len(animation_database[headquarter_action]):
        headquarter_frame = 0
    headquarter_img_id = animation_database[headquarter_action][headquarter_frame]
    headquarter_img = animation_frames[headquarter_img_id]
    display.blit(pygame.transform.flip(headquarter_img, headquarter_flip, False), (headquarter_rect.x-scroll[0], headquarter_rect.y-scroll[1]))

    tree_frame += 1
    if tree_frame >= len(animation_database[tree_action]):
        tree_frame = 0
    tree_img_id = animation_database[tree_action][tree_frame]
    tree_img = animation_frames[tree_img_id]
    display.blit(pygame.transform.flip(tree_img, tree_flip, False), (tree_rect.x-scroll[0], tree_rect.y-scroll[1]))

    player_frame += 1
    if player_frame >= len(animation_database[player_action]):
        player_frame = 0
    player_img_id = animation_database[player_action][player_frame]
    player_img = animation_frames[player_img_id]
    display.blit(pygame.transform.flip(player_img,player_flip,False),(player_rect.x-scroll[0],player_rect.y-scroll[1]))

    for event in pygame.event.get(): # event loop
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_x:
                pygame.mixer.music.fadeout(1000)
            if event.key == K_d:
                moving_right = True
            if event.key == K_a:
                moving_left = True
            if event.key == K_SPACE:
                if air_timer < 6:
                    jump_sound.play()
                    player_vertical_momentum = -5
            if event.key == K_h: #press 'h' to decrease hp
                player_hp = max(0, player_hp - 10)
            if event.key == K_g: #press 'g' to increase hp
                player_hp = max(0, player_hp + 10)
        if event.type == KEYUP:
            if event.key == K_d:
                moving_right = False
            if event.key == K_a:
                moving_left = False
    #DREW THE DOOR FOR DEBUG
    #pygame.draw.rect(display, (255,0,0), (door_rect.x-scroll[0], door_rect.y-scroll[1], door_rect.width, door_rect.height), 1)
    screen.blit(pygame.transform.scale(display,WINDOW_SIZE),(0,0))
    pygame.display.update()
    clock.tick(60)
