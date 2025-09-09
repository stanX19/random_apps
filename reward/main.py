import math
import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Screen dimensions
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Reward Button with Particles")

# Colors
black = (0, 0, 0)
green = (0, 255, 0)
white = (255, 255, 255)
particle_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 165, 0),
                   (128, 0, 128)]  # Added orange and purple

# Button properties
button_x = screen_width // 2
button_y = screen_height // 2
button_radius = 60
button_color = green
button_border_color = white
button_border_width = 3

# Text properties
font = pygame.font.Font(None, 36)
text = "REWARD"
text_color = white
text_surface = font.render(text, True, text_color)
text_rect = text_surface.get_rect(center=(button_x, button_y))

# Particle properties
particles = []
particle_count = 40
particle_speed = 24
particle_radius = 5
gravity = 0.3
air_resistance = 0.98
velocity_limit = 100  # Added velocity limit

# Collision properties
cell_size = 30  # Increased cell size for fewer checks
overlap_epsilon = 0.1 # Added overlap epsilon to prevent 100% overlap

class Particle:
    def __init__(self, x, y, x_vel, y_vel, color, radius):
        self.x = x
        self.y = y
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.color = color
        self.radius = radius
        self.mass = radius  # Simple mass approximation

    def update(self):
        self.x += self.x_vel
        self.y += self.y_vel
        self.y_vel += gravity  # Apply gravity
        self.x_vel *= air_resistance  # Apply air resistance
        self.y_vel *= air_resistance

        # Apply velocity limit
        speed = math.sqrt(self.x_vel**2 + self.y_vel**2)
        if speed > velocity_limit:
            self.x_vel = (self.x_vel / speed) * velocity_limit
            self.y_vel = (self.y_vel / speed) * velocity_limit

        # Bounce from borders (with slight energy loss)
        if self.x + self.radius > screen_width:
            if self.x_vel > 0:
                self.x_vel *= -1
            self.x = screen_width - self.radius
        elif self.x - self.radius < 0:
            if self.x_vel < 0:
                self.x_vel *= -1
            self.x = self.radius
        if self.y + self.radius > screen_height:
            if self.y_vel > 0:
                self.y_vel *= -1
            self.y = screen_height - self.radius
        elif self.y - self.radius < 0:
            if self.y_vel < 0:
                self.y_vel *= -1
            self.y = self.radius

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

def is_colliding(a, b):
    """Simple circle collision detection."""
    distance_squared = (a.x - b.x) ** 2 + (a.y - b.y) ** 2
    return distance_squared <= (a.radius + b.radius + overlap_epsilon) ** 2 # Added epsilon

def create_particles(center_x, center_y, radius):
    for _ in range(particle_count):
        angle = random.uniform(0, 2 * math.pi)
        spawn_x = center_x + radius * math.cos(angle)
        spawn_y = center_y + radius * math.sin(angle)
        speed = random.uniform(particle_speed * 0.5, particle_speed)
        x_vel = speed * math.cos(angle)
        y_vel = speed * math.sin(angle)
        color = random.choice(particle_colors)
        particle_rad = particle_radius
        particles.append(Particle(spawn_x, spawn_y, x_vel, y_vel, color, particle_rad))

def assign_to_cells(particles, cell_size):
    """Assigns particles to grid cells based on their positions."""
    cells = {}
    for i, particle in enumerate(particles):
        x, y = int(particle.x), int(particle.y)
        cell_x = int(x // cell_size)
        cell_y = int(y // cell_size)
        if (cell_x, cell_y) not in cells:
            cells[(cell_x, cell_y)] = []
        cells[(cell_x, cell_y)].append(i)
    return cells

def get_neighboring_cells(cell_x, cell_y):
    """Returns the coordinates of a cell and its eight neighbors."""
    return [(cell_x + dx, cell_y + dy) for dx in range(-1, 2) for dy in range(-1, 2)]

def check_collisions_within_cells(particles, cell_size):
    """Checks collisions and applies hard repulsion between particles."""
    collisions = []
    cells = assign_to_cells(particles, cell_size)

    for cell_coords, particle_indices in cells.items():
        for index_a in particle_indices:
            for index_b in particle_indices:
                if index_a != index_b:
                    particle_a = particles[index_a]
                    particle_b = particles[index_b]
                    if is_colliding(particle_a, particle_b):
                        collisions.append((index_a, index_b))
                        # Calculate overlap and direction
                        dx = particle_b.x - particle_a.x
                        dy = particle_b.y - particle_a.y
                        distance = math.sqrt(dx * dx + dy * dy)
                        overlap = particle_a.radius + particle_b.radius - distance
                        if distance > 0:
                            nx = dx / distance
                            ny = dy / distance
                        else:
                            nx = random.uniform(-1, 1)
                            ny = random.uniform(-1, 1)

                        # Move particles apart by the overlap amount
                        move_x = overlap * nx
                        move_y = overlap * ny

                        # Adjust particle positions directly
                        particle_a.x -= move_x * 0.5
                        particle_a.y -= move_y * 0.5
                        particle_b.x += move_x * 0.5
                        particle_b.y += move_y * 0.5

                        # Calculate relative velocity
                        relative_x_velocity = particle_b.x_vel - particle_a.x_vel
                        relative_y_velocity = particle_b.y_vel - particle_a.y_vel

                        # Calculate dot product of relative velocity and collision normal
                        dot_product = relative_x_velocity * nx + relative_y_velocity * ny

                        # If particles are moving towards each other
                        if dot_product < 0:
                            # Calculate the combined velocity of the particles along the collision normal
                            combined_velocity = -dot_product

                            # Calculate the masses
                            m1 = particle_a.mass
                            m2 = particle_b.mass

                            # Calculate the velocities of the particles after the collision
                            v1_x = (particle_a.x_vel * (m1 - m2) + 2 * m2 * particle_b.x_vel) / (m1 + m2)
                            v1_y = (particle_a.y_vel * (m1 - m2) + 2 * m2 * particle_b.y_vel) / (m1 + m2)
                            v2_x = (particle_b.x_vel * (m2 - m1) + 2 * m1 * particle_a.x_vel) / (m1 + m2)
                            v2_y = (particle_b.y_vel * (m2 - m1) + 2 * m1 * particle_a.y_vel) / (m1 + m2)

                            # Apply velocity limit
                            speed_a = math.sqrt(v1_x**2 + v1_y**2)
                            if speed_a > velocity_limit:
                                v1_x = (v1_x / speed_a) * velocity_limit
                                v1_y = (v1_y / speed_a) * velocity_limit
                            speed_b = math.sqrt(v2_x**2 + v2_y**2)
                            if speed_b > velocity_limit:
                                v2_x = (v2_x / speed_b) * velocity_limit
                                v2_y = (v2_y / speed_b) * velocity_limit

                            # Update velocities
                            particle_a.x_vel = v1_x
                            particle_a.y_vel = v1_y
                            particle_b.x_vel = v2_x
                            particle_b.y_vel = v2_y



# Game loop
running = True
clock = pygame.time.Clock()
while running:
    clock.tick(30)  # Cap frame rate

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            distance = math.sqrt((mouse_x - button_x) ** 2 + (mouse_y - button_y) ** 2)
            if distance <= button_radius:
                create_particles(button_x, button_y, button_radius)  # Spawn from edge

    # Update particles
    for particle in particles[:]:
        particle.update()

    # Check for collisions and apply repulsion
    collisions = check_collisions_within_cells(particles, cell_size)

    # Draw everything
    screen.fill(black)

    # Draw button border
    pygame.draw.circle(screen, button_border_color, (button_x, button_y),
                       button_radius + button_border_width)
    # Draw button
    pygame.draw.circle(screen, button_color, (button_x, button_y), button_radius)
    # Draw text
    screen.blit(text_surface, text_rect)

    # Draw particles
    for particle in particles:
        particle.draw(screen)

    pygame.display.flip()

pygame.quit()
