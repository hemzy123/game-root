import pygame
import os

class ExplosionEffect(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames = []
        self.load_frames()
        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=(x, y))
        self.frame_delay = 5  # frames to wait before advancing
        self.frame_count = 0
    
    def load_frames(self):
        # Load the sprite sheet
        path = os.path.join("assets", "effects", "explosion", "explosion_spritesheet.png")
        sheet = pygame.image.load(path).convert_alpha()
        frame_width = sheet.get_width() // 3
        frame_height = sheet.get_height() // 3
        for row in range(3):
            for col in range(3):
                frame = sheet.subsurface(
                    (col * frame_width, row * frame_height, frame_width, frame_height)
                )
                self.frames.append(frame)
    
    def update(self):
        self.frame_count += 1
        if self.frame_count >= self.frame_delay:
            self.frame_count = 0
            self.current_frame += 1
            if self.current_frame < len(self.frames):
                self.image = self.frames[self.current_frame]
            else:
                self.kill()  # remove explosion when done

# Example usage in a game loop:
def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Explosion Effect")
    clock = pygame.time.Clock()
    
    # Create a sprite group to hold the explosion
    all_sprites = pygame.sprite.Group()
    
    # Main game loop
    running = True
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Create a new explosion at mouse position
                explosion = ExplosionEffect(*event.pos)
                all_sprites.add(explosion)
        
        # Update
        all_sprites.update()
        
        # Draw
        screen.fill((0, 0, 0))  # Black background
        all_sprites.draw(screen)
        pygame.display.flip()
        
        # Cap at 60 FPS
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()