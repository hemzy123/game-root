import math
import numpy as np

class GravitySystem:
    """
    Handles gravity calculations and effects for game objects.
    This system can be used for standard downward gravity as well as
    custom gravitational fields and effects.
    """
    
    def __init__(self, gravity_constant=9.81, gravity_direction=np.array([0, -1, 0])):
        """
        Initialize the gravity system.
        
        Args:
            gravity_constant: The strength of gravity (default: 9.81 m/s²)
            gravity_direction: The normalized direction of gravity (default: downward)
        """
        self.gravity_constant = gravity_constant
        self.gravity_direction = gravity_direction / np.linalg.norm(gravity_direction)
        self.gravity_vector = self.gravity_direction * self.gravity_constant
        self.affected_objects = []
        
    def register_object(self, game_object):
        """
        Register a game object to be affected by gravity.
        
        Args:
            game_object: The game object to register
        """
        if game_object not in self.affected_objects:
            self.affected_objects.append(game_object)
            
    def unregister_object(self, game_object):
        """
        Unregister a game object from gravity effects.
        
        Args:
            game_object: The game object to unregister
        """
        if game_object in self.affected_objects:
            self.affected_objects.remove(game_object)
    
    def apply_gravity(self, game_object, delta_time):
        """
        Apply gravity to a specific game object.
        
        Args:
            game_object: The game object to apply gravity to
            delta_time: Time elapsed since the last update
        """
        if hasattr(game_object, 'velocity') and hasattr(game_object, 'mass'):
            # F = ma, so a = F/m
            # In this case, F = mg, so a = g
            # We ignore mass for standard gravity (as in real physics)
            acceleration = self.gravity_vector
            
            # Update velocity: v = v₀ + at
            game_object.velocity += acceleration * delta_time
            
    def apply_custom_gravity(self, game_object, attractor, attractor_mass, delta_time, 
                             min_distance=1.0, gravity_constant=6.674e-11):
        """
        Apply gravitational attraction between objects (like planetary gravity).
        
        Args:
            game_object: The object being affected by gravity
            attractor: The object creating the gravitational field
            attractor_mass: Mass of the attractor object
            delta_time: Time elapsed since the last update
            min_distance: Minimum distance to prevent infinite acceleration
            gravity_constant: Universal gravitational constant (default: 6.674×10⁻¹¹ N⋅m²/kg²)
        """
        if hasattr(game_object, 'position') and hasattr(game_object, 'velocity') and hasattr(game_object, 'mass'):
            # Calculate direction vector from object to attractor
            direction = attractor.position - game_object.position
            distance = max(np.linalg.norm(direction), min_distance)
            
            # Normalize direction
            if distance > 0:
                direction = direction / distance
            
            # Calculate gravitational force: F = G * (m1 * m2) / r²
            force_magnitude = gravity_constant * (game_object.mass * attractor_mass) / (distance * distance)
            
            # Calculate acceleration: a = F/m
            acceleration = direction * (force_magnitude / game_object.mass)
            
            # Update velocity: v = v₀ + at
            game_object.velocity += acceleration * delta_time
    
    def update(self, delta_time):
        """
        Update all registered objects with gravity effects.
        
        Args:
            delta_time: Time elapsed since the last update
        """
        for obj in self.affected_objects:
            self.apply_gravity(obj, delta_time)
    
    def set_gravity_strength(self, gravity_constant):
        """
        Set the strength of the gravity constant.
        
        Args:
            gravity_constant: New gravity strength
        """
        self.gravity_constant = gravity_constant
        self.gravity_vector = self.gravity_direction * self.gravity_constant
    
    def set_gravity_direction(self, gravity_direction):
        """
        Set the direction of gravity.
        
        Args:
            gravity_direction: New gravity direction vector (will be normalized)
        """
        self.gravity_direction = gravity_direction / np.linalg.norm(gravity_direction)
        self.gravity_vector = self.gravity_direction * self.gravity_constant
    
    def disable_gravity(self):
        """Temporarily disable gravity by setting constant to 0"""
        self.set_gravity_strength(0)
    
    def enable_gravity(self, gravity_constant=9.81):
        """Re-enable gravity with specified strength"""
        self.set_gravity_strength(gravity_constant)


class GravityZone:
    """
    Defines a zone with custom gravity properties.
    Can be used for special areas with different gravity effects.
    """
    
    def __init__(self, position, radius, gravity_modifier=1.0, 
                 gravity_direction=None, is_enabled=True):
        """
        Initialize a gravity zone.
        
        Args:
            position: Position of the zone center
            radius: Radius of the zone's influence
            gravity_modifier: Multiplier for gravity strength inside the zone
            gravity_direction: Custom gravity direction inside the zone (None = use global)
            is_enabled: Whether the zone is active
        """
        self.position = np.array(position)
        self.radius = radius
        self.gravity_modifier = gravity_modifier
        self.gravity_direction = gravity_direction
        self.is_enabled = is_enabled
    
    def is_in_zone(self, object_position):
        """
        Check if an object is within this gravity zone.
        
        Args:
            object_position: Position to check
            
        Returns:
            bool: True if position is within zone
        """
        distance = np.linalg.norm(np.array(object_position) - self.position)
        return distance <= self.radius
    
    def get_influence_factor(self, object_position):
        """
        Calculate how strongly the zone affects an object based on distance.
        Objects at the edge are less affected than objects at center.
        
        Args:
            object_position: Position to check
            
        Returns:
            float: Influence factor (0-1)
        """
        if not self.is_in_zone(object_position):
            return 0.0
            
        distance = np.linalg.norm(np.array(object_position) - self.position)
        # Linear falloff from center (1.0) to edge (0.0)
        return 1.0 - (distance / self.radius)
    
    def modify_gravity(self, gravity_system, object_position, influence_threshold=0.05):
        """
        Apply this zone's gravity modification to the gravity system.
        
        Args:
            gravity_system: The GravitySystem to modify
            object_position: Position of the object to affect
            influence_threshold: Minimum influence factor to apply modifications
        
        Returns:
            tuple: Modified (gravity_constant, gravity_direction)
        """
        if not self.is_enabled:
            return (gravity_system.gravity_constant, gravity_system.gravity_direction)
            
        influence = self.get_influence_factor(object_position)
        
        if influence <= influence_threshold:
            return (gravity_system.gravity_constant, gravity_system.gravity_direction)
        
        # Modify gravity strength
        modified_constant = gravity_system.gravity_constant * self.gravity_modifier
        
        # Modify gravity direction if specified
        if self.gravity_direction is not None:
            normalized_direction = self.gravity_direction / np.linalg.norm(self.gravity_direction)
            # Interpolate between original and zone direction based on influence
            blended_direction = (1 - influence) * gravity_system.gravity_direction + influence * normalized_direction
            modified_direction = blended_direction / np.linalg.norm(blended_direction)
        else:
            modified_direction = gravity_system.gravity_direction
            
        return (modified_constant, modified_direction)