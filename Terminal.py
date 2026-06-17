import os
import pty
import select
import subprocess
import sys
import fcntl
import termios
import struct

try:
    import pygame
except ImportError as exc:
    print("Missing dependency: pygame. Install it with: python3 -m pip install pygame")
    raise SystemExit(1) from exc

try:
    import pyte # type: ignore
except ImportError as exc:
    print("Missing dependency: pyte. Install it with: python3 -m pip install pyte")
    raise SystemExit(1) from exc

# --- Initial Configuration ---
FONT_SIZE = 14
BG_COLOR = (0, 0, 0)

class AdjustableTerminal:
    def __init__(self):
        pygame.init()
        # Use a reliable monospace font
        self.font = pygame.font.SysFont("dejavusansmono", FONT_SIZE)
        self.char_width, self.char_height = self.font.size("A")
        
        # Initial Window Size
        self.win_width, self.win_height = 900, 600
        self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
        pygame.display.set_caption("Adjustable Hollywood Shell")
        
        # Calculate initial Grid
        self.cols = self.win_width // self.char_width
        self.rows = self.win_height // self.char_height
        
        self.screen_buffer = pyte.Screen(self.cols, self.rows)
        self.stream = pyte.ByteStream(self.screen_buffer)
        
        self.master_fd, self.slave_fd = pty.openpty()
        self.update_pty_size()

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        
        self.process = subprocess.Popen(
            ["/bin/bash"],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            start_new_session=True,
            env=env
        )
        self.running = True

    def update_pty_size(self):
        """Tells the Linux Kernel the new window dimensions."""
        winsize = struct.pack("HHHH", self.rows, self.cols, 0, 0)
        fcntl.ioctl(self.slave_fd, termios.TIOCSWINSZ, winsize)
        # Also update the pyte buffer to match
        self.screen_buffer = pyte.Screen(self.cols, self.rows)
        self.stream = pyte.ByteStream(self.screen_buffer)

    def handle_resize(self, new_w, new_h):
        """Calculates new grid based on pixel size."""
        self.win_width, self.win_height = new_w, new_h
        self.cols = max(1, self.win_width // self.char_width)
        self.rows = max(1, self.win_height // self.char_height)
        self.update_pty_size()

    def update_terminal(self):
        while True:
            r, _, _ = select.select([self.master_fd], [], [], 0)
            if r:
                try:
                    data = os.read(self.master_fd, 10240)
                    self.stream.feed(data)
                except OSError:
                    self.running = False
                    break
            else:
                break

    def draw(self):
        self.screen.fill(BG_COLOR)
        # Render the pyte buffer
        for y, line in enumerate(self.screen_buffer.display):
            for x, char in enumerate(line):
                if char == " ": continue
                
                char_info = self.screen_buffer.buffer[y][x]
                color = char_info.fg
                
                if color == 'default': rgb = (0, 255, 65)
                else:
                    try: rgb = pygame.Color(color)
                    except: rgb = (0, 255, 65)

                txt_surface = self.font.render(char, True, rgb)
                self.screen.blit(txt_surface, (x * self.char_width, y * self.char_height))
        
        pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.update_terminal()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        os.write(self.master_fd, b"\r")
                    elif event.key == pygame.K_BACKSPACE:
                        os.write(self.master_fd, b"\x7f")
                    else:
                        try:
                            os.write(self.master_fd, event.unicode.encode('utf-8'))
                        except: pass

            self.draw()
            clock.tick(30)
        pygame.quit()

if __name__ == "__main__":
    AdjustableTerminal().run()


