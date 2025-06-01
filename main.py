import pygame
import threading
import json
import os
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import time
import random

pygame.font.init()
WIDTH, HEIGHT = 1000, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Meteroid Dodge")

# Load images
BG = pygame.transform.scale(pygame.image.load("bgimage.jpg"), (WIDTH, HEIGHT))
PLAYER_WIDTH, PLAYER_HEIGHT = 60, 80
PLAYER_IMAGE = pygame.transform.scale(pygame.image.load("player.png"), (PLAYER_WIDTH, PLAYER_HEIGHT))
METEOR_IMAGE = pygame.transform.scale(pygame.image.load("meteor.png"), (30, 40))

# Game settings
KEYBOARD_VEL = 5
VOICE_VEL = 3
STAR_VEL = 2
FONT = pygame.font.SysFont("comicsans", 30)
BIG_FONT = pygame.font.SysFont("comicsans", 60)
HIGH_SCORE_FILE = "high_score.txt"

run = True
voice_direction = None
voice_lock = threading.Lock()

def get_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        with open(HIGH_SCORE_FILE, "r") as file:
            return float(file.read().strip())
    return 0.0

def save_high_score(score):
    with open(HIGH_SCORE_FILE, "w") as file:
        file.write(str(score))

def draw(player, elapsed_time, stars, score, high_score):
    WIN.blit(BG, (0, 0))
    time_text = FONT.render(f"Time: {int(elapsed_time)}s", True, (255, 255, 255))
    score_text = FONT.render(f"Score: {int(score)}", True, (255, 255, 255))
    high_score_text = FONT.render(f"High Score: {int(high_score)}", True, (255, 255, 0))

    WIN.blit(time_text, (10, 10))
    WIN.blit(score_text, (10, 40))
    WIN.blit(high_score_text, (10, 70))

    WIN.blit(PLAYER_IMAGE, (player.x, player.y))
    for star in stars:
        WIN.blit(METEOR_IMAGE, (star.x, star.y))

    pygame.display.update()

def listen_for_voice_commands():
    global run, voice_direction
    model = Model("model")
    rec = KaldiRecognizer(model, 16000)

    def callback(indata, frames, time_, status):
        global run, voice_direction

        if rec.AcceptWaveform(bytes(indata)):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            print(f"You said (full): {text}")

            with voice_lock:
                if "close" in text:
                    run = False
                elif "left" in text:
                    voice_direction = "left"
                elif "right" in text:
                    voice_direction = "right"
                elif "stop" in text:
                    voice_direction = None
        else:
            partial = json.loads(rec.PartialResult()).get("partial", "")
            with voice_lock:
                if "left" in partial:
                    voice_direction = "left"
                elif "right" in partial:
                    voice_direction = "right"
                elif "stop" in partial:
                    voice_direction = None

    with sd.RawInputStream(samplerate=16000, blocksize=2048, dtype='int16',
                           channels=1, callback=callback, latency='low'):
        print("Listening for voice commands...")
        while run:
            sd.sleep(10)

def start_screen():
    WIN.blit(BG, (0, 0))
    title = BIG_FONT.render("Meteroid attack", True, "white")
    msg = FONT.render("Say 'start' or press ENTER to begin. Say 'close' to exit.", True, "white")
    WIN.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 100))
    WIN.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))
    pygame.display.update()

    started = False
    closed = False

    def listen_start():
        nonlocal started, closed
        model = Model("model")
        rec = KaldiRecognizer(model, 16000)

        def callback(indata, frames, time_, status):
            nonlocal started, closed
            if rec.AcceptWaveform(bytes(indata)):
                result = json.loads(rec.Result()).get("text", "")
                print(f"You said (start screen): {result}")
                if "start" in result:
                    started = True
                elif "close" in result:
                    closed = True

        with sd.RawInputStream(samplerate=16000, blocksize=2048, dtype='int16',
                               channels=1, callback=callback, latency='low'):
            while not started and not closed:
                sd.sleep(100)

    thread = threading.Thread(target=listen_start)
    thread.daemon = True
    thread.start()

    while not started and not closed:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    started = True
                elif event.key == pygame.K_ESCAPE:
                    closed = True

    if closed:
        pygame.quit()
        quit()


def game_over_screen(final_score, high_score):
    global run
    WIN.blit(BG, (0, 0))
    lost_text = BIG_FONT.render("You Lost!", True, "red")
    score_text = FONT.render(f"Score: {int(final_score)}", True, "white")
    high_score_text = FONT.render(f"High Score: {int(high_score)}", True, "yellow")
    restart_text = FONT.render("Say 'start again' or press ENTER to restart", True, "white")
    close_text = FONT.render("Say 'close' or press ESC to exit", True, "white")

    WIN.blit(lost_text, (WIDTH//2 - lost_text.get_width()//2, HEIGHT//2 - 100))
    WIN.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2 - 40))
    WIN.blit(high_score_text, (WIDTH//2 - high_score_text.get_width()//2, HEIGHT//2))
    WIN.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 60))
    WIN.blit(close_text, (WIDTH//2 - close_text.get_width()//2, HEIGHT//2 + 100))
    pygame.display.update()

    choice_made = False
    start_again = False

    def listen_game_over_choice():
        nonlocal choice_made, start_again
        model = Model("model")
        rec = KaldiRecognizer(model, 16000)

        def callback(indata, frames, time_, status):
            nonlocal choice_made, start_again
            if rec.AcceptWaveform(bytes(indata)):
                result = json.loads(rec.Result()).get("text", "")
                print(f"You said (game over): {result}")
                if "start again" in result:
                    start_again = True
                    choice_made = True
                elif "close" in result:
                    choice_made = True

        with sd.RawInputStream(samplerate=16000, blocksize=2048, dtype='int16',
                               channels=1, callback=callback, latency='low'):
            while not choice_made:
                sd.sleep(100)

    thread = threading.Thread(target=listen_game_over_choice)
    thread.start()

    while not choice_made:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                choice_made = True
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    start_again = True
                    choice_made = True
                elif event.key == pygame.K_ESCAPE:
                    choice_made = True
                    run = False

    return start_again


def main():
    
    global run, voice_direction
    voice_direction = None 
    start_screen()

    voice_thread = threading.Thread(target=listen_for_voice_commands)
    voice_thread.daemon = True
    voice_thread.start()

    player = pygame.Rect(WIDTH//2, HEIGHT - PLAYER_HEIGHT, PLAYER_WIDTH, PLAYER_HEIGHT)
    clock = pygame.time.Clock()
    start_time = time.time()
    elapsed_time = 0
    star_add_increment = 2000
    star_count = 0
    stars = []
    hit = False

    score = 0
    high_score = get_high_score()

    while run:
        star_count += clock.tick(60)
        elapsed_time = time.time() - start_time
        score = elapsed_time

        if star_count > star_add_increment:
            for _ in range(3):
                star_x = random.randint(0, WIDTH - 30)
                star = pygame.Rect(star_x, -40, 30, 40)
                stars.append(star)
            star_add_increment = max(200, star_add_increment - 50)
            star_count = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player.x - KEYBOARD_VEL > 0:
            player.x -= KEYBOARD_VEL
        if keys[pygame.K_RIGHT] and player.x + KEYBOARD_VEL < WIDTH - PLAYER_WIDTH:
            player.x += KEYBOARD_VEL

        with voice_lock:
            if voice_direction == "left" and player.x - VOICE_VEL > 0:
                player.x -= VOICE_VEL
            elif voice_direction == "right" and player.x + VOICE_VEL < WIDTH - PLAYER_WIDTH:
                player.x += VOICE_VEL

        for star in stars[:]:
            star.y += STAR_VEL
            if star.y > HEIGHT:
                stars.remove(star)
            elif star.colliderect(player):
                hit = True
                break

        if hit:
            if score > high_score:
                save_high_score(score)
                high_score = score
            if game_over_screen(score, high_score):
                main()  # Restart game
            break


        draw(player, elapsed_time, stars, score, high_score)

    pygame.quit()

if __name__ == "__main__":
    main()
