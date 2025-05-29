import numpy as np
import math
from typing import Dict, Tuple, List, Optional, Any

class Motion:
    """
    Main motion physics class that handles object movement, velocity, 
    acceleration, and various movement types including omni-directional movement.
    """
    
    def __init__(self):
        # Default physics constants
        self.gravity = np.array([0.0, -9.81, 0.0])  # Default gravity vector (y-down)
        self.air_resistance = 0.01                   # Default air resistance coefficient
        self.ground_friction = 0.1                   # Default ground friction coefficient
    
    def set_gravity(self, gravity_vector: np.ndarray):
        """
        Set the global gravity vector.
        
        Args:
            gravity_vector: 3D vector representing gravity direction and magnitude
        """
        self.gravity = gravity_vector
    
    def set_friction_coefficients(self, air_resistance: float, ground_friction: float):
        """
        Set global friction coefficients.
        
        Args:
            air_resistance: Coefficient for air resistance (0-1)
            ground_friction: Coefficient for ground friction (0-1)
        """
        self.air_resistance = air_resistance
        self.ground_friction = ground_friction
    
    def apply_force(self, mass: float, current_velocity: np.ndarray, 
                   force: np.ndarray, delta_time: float) -> np.ndarray:
        """
        Apply a force to an object based on F = ma.
        
        Args:
            mass: Mass of the object
            current_velocity: Current velocity vector
            force: Force vector to apply
            delta_time: Time step in seconds
            
        Returns:
            New velocity after applying the force
        """
        # F = ma, so a = F/m
        acceleration = force / mass
        
        # v = v0 + at
        new_velocity = current_velocity + acceleration * delta_time
        
        return new_velocity
    
    def apply_impulse(self, mass: float, current_velocity: np.ndarray, 
                     impulse: np.ndarray) -> np.ndarray:
        """
        Apply an instantaneous impulse to an object.
        Impulse is a change in momentum (J = m * Δv).
        
        Args:
            mass: Mass of the object
            current_velocity: Current velocity vector
            impulse: Impulse vector to apply
            
        Returns:
            New velocity after applying the impulse
        """
        # J = m * Δv, so Δv = J/m
        velocity_change = impulse / mass
        
        # v = v0 + Δv
        new_velocity = current_velocity + velocity_change
        
        return new_velocity
    
    def apply_gravity(self, velocity: np.ndarray, is_grounded: bool, 
                     delta_time: float) -> np.ndarray:
        """
        Apply gravity to an object if it's not grounded.
        
        Args:
            velocity: Current velocity vector
            is_grounded: Whether the object is on the ground
            delta_time: Time step in seconds
            
        Returns:
            New velocity after applying gravity
        """
        if not is_grounded:
            # Apply gravity acceleration: v = v0 + gt
            return velocity + self.gravity * delta_time
        
        return velocity
    
    def apply_air_resistance(self, velocity: np.ndarray, delta_time: float) -> np.ndarray:
        """
        Apply air resistance to slow down an object.
        
        Args:
            velocity: Current velocity vector
            delta_time: Time step in seconds
            
        Returns:
            New velocity after applying air resistance
        """
        # Simple linear air resistance model: F = -kv
        # For more realism, could use quadratic: F = -kv²
        speed = np.linalg.norm(velocity)
        
        if speed > 0.001:  # Avoid division by zero
            # Deceleration proportional to velocity
            deceleration = -self.air_resistance * velocity
            
            # Apply deceleration
            new_velocity = velocity + deceleration * delta_time
            
            # Prevent oscillation around zero
            new_speed = np.linalg.norm(new_velocity)
            if new_speed < 0.001 or np.dot(new_velocity, velocity) < 0:
                return np.zeros_like(velocity)
                
            return new_velocity
            
        return np.zeros_like(velocity)
    
    def apply_ground_friction(self, velocity: np.ndarray, 
                             is_grounded: bool, delta_time: float) -> np.ndarray:
        """
        Apply ground friction to slow down a grounded object.
        
        Args:
            velocity: Current velocity vector
            is_grounded: Whether the object is on the ground
            delta_time: Time step in seconds
            
        Returns:
            New velocity after applying ground friction
        """
        if not is_grounded:
            return velocity
            
        # Extract horizontal component (assuming y is up)
        horizontal_velocity = np.array([velocity[0], 0.0, velocity[2]])
        speed = np.linalg.norm(horizontal_velocity)
        
        if speed > 0.001:  # Avoid division by zero
            # Friction force opposes motion direction
            friction_direction = -horizontal_velocity / speed
            
            # Deceleration proportional to coefficient of friction
            deceleration = friction_direction * self.ground_friction * 9.81  # 9.81 is gravity magnitude
            
            # Apply to horizontal velocity
            new_horizontal = horizontal_velocity + deceleration * delta_time
            
            # Prevent oscillation around zero
            new_speed = np.linalg.norm(new_horizontal)
            if new_speed < 0.001 or np.dot(new_horizontal, horizontal_velocity) < 0:
                new_horizontal = np.zeros_like(horizontal_velocity)
            
            # Recombine with vertical component
            new_velocity = np.array([new_horizontal[0], velocity[1], new_horizontal[2]])
            return new_velocity
            
        # If speed is near-zero, just zero out horizontal movement
        return np.array([0.0, velocity[1], 0.0])
    
    def update_position(self, position: np.ndarray, velocity: np.ndarray, 
                       delta_time: float) -> np.ndarray:
        """
        Update position based on velocity.
        
        Args:
            position: Current position vector
            velocity: Current velocity vector
            delta_time: Time step in seconds
            
        Returns:
            New position
        """
        # Simple integration: x = x0 + vt
        return position + velocity * delta_time
    
    def process_object_motion(self, obj: Dict[str, Any], delta_time: float) -> Dict[str, Any]:
        """
        Process all motion physics for a single object.
        
        Args:
            obj: Object data containing position, velocity, mass, etc.
            delta_time: Time step in seconds
            
        Returns:
            Updated object data
        """
        # Make a copy to avoid modifying the original
        updated_obj = obj.copy()
        
        # Apply gravity if not grounded
        updated_obj['velocity'] = self.apply_gravity(
            updated_obj['velocity'], 
            updated_obj.get('is_grounded', False), 
            delta_time
        )
        
        # Apply air resistance
        updated_obj['velocity'] = self.apply_air_resistance(
            updated_obj['velocity'], 
            delta_time
        )
        
        # Apply ground friction
        updated_obj['velocity'] = self.apply_ground_friction(
            updated_obj['velocity'],
            updated_obj.get('is_grounded', False),
            delta_time
        )
        
        # Update position
        updated_obj['position'] = self.update_position(
            updated_obj['position'],
            updated_obj['velocity'],
            delta_time
        )
        
        return updated_obj


class OmniMovement:
    """
    Handles omni-directional movement for player characters or AI.
    Supports strafing, quick direction changes, and dynamic control.
    """
    
    def __init__(self, motion_system: Motion):
        """
        Initialize omni movement controller.
        
        Args:
            motion_system: Reference to the main motion physics system
        """
        self.motion = motion_system
        
        # Movement parameters
        self.max_speed = 5.0                # Maximum movement speed (m/s)
        self.acceleration = 20.0            # Movement acceleration (m/s²)
        self.deceleration = 25.0            # Movement deceleration when stopping (m/s²)
        self.air_control = 0.3              # Amount of control in air (0-1)
        self.strafe_speed_multiplier = 0.8  # Multiplier for strafing speed
        self.backward_speed_multiplier = 0.7 # Multiplier for backward movement
        self.sprint_multiplier = 1.5        # Speed multiplier when sprinting
        self.crouch_multiplier = 0.5        # Speed multiplier when crouching
    
    def set_movement_params(self, max_speed: float = None, acceleration: float = None, 
                           deceleration: float = None, air_control: float = None,
                           strafe_multiplier: float = None, backward_multiplier: float = None,
                           sprint_multiplier: float = None, crouch_multiplier: float = None):
        """
        Set movement parameters.
        
        Args:
            max_speed: Maximum movement speed
            acceleration: Movement acceleration
            deceleration: Movement deceleration when stopping
            air_control: Amount of control in air (0-1)
            strafe_multiplier: Multiplier for strafing speed
            backward_multiplier: Multiplier for backward movement
            sprint_multiplier: Speed multiplier when sprinting
            crouch_multiplier: Speed multiplier when crouching
        """
        if max_speed is not None:
            self.max_speed = max_speed
        if acceleration is not None:
            self.acceleration = acceleration
        if deceleration is not None:
            self.deceleration = deceleration
        if air_control is not None:
            self.air_control = max(0.0, min(1.0, air_control))  # Clamp to 0-1
        if strafe_multiplier is not None:
            self.strafe_speed_multiplier = strafe_multiplier
        if backward_multiplier is not None:
            self.backward_speed_multiplier = backward_multiplier
        if sprint_multiplier is not None:
            self.sprint_multiplier = sprint_multiplier
        if crouch_multiplier is not None:
            self.crouch_multiplier = crouch_multiplier
    
    def calculate_move_direction(self, forward_vec: np.ndarray, right_vec: np.ndarray,
                                input_direction: np.ndarray) -> np.ndarray:
        """
        Calculate movement direction based on input and facing direction.
        
        Args:
            forward_vec: Character's forward vector (normalized)
            right_vec: Character's right vector (normalized)
            input_direction: Input direction vector (x: right/left, z: forward/backward)
            
        Returns:
            Movement direction vector (normalized)
        """
        # Scale the vectors by input
        forward_component = forward_vec * input_direction[2]  # Z is forward/backward
        right_component = right_vec * input_direction[0]      # X is right/left
        
        # Combine vectors
        move_direction = forward_component + right_component
        
        # Normalize if non-zero
        magnitude = np.linalg.norm(move_direction)
        if magnitude > 0.001:
            move_direction = move_direction / magnitude
            
        return move_direction
    
    def apply_movement_input(self, obj: Dict[str, Any], input_direction: np.ndarray, 
                            delta_time: float, is_sprinting: bool = False, 
                            is_crouching: bool = False) -> Dict[str, Any]:
        """
        Apply input-based movement to an object with omni-directional control.
        
        Args:
            obj: Object data containing position, velocity, forward_vector, etc.
            input_direction: Input direction vector (x: right/left, z: forward/backward)
            delta_time: Time step in seconds
            is_sprinting: Whether the character is sprinting
            is_crouching: Whether the character is crouching
            
        Returns:
            Updated object data
        """
        # Make a copy to avoid modifying the original
        updated_obj = obj.copy()
        
        # Get character orientation vectors
        forward_vec = obj.get('forward_vector', np.array([0.0, 0.0, 1.0]))
        
        # Calculate right vector (assuming Y is up)
        right_vec = np.cross(np.array([0.0, 1.0, 0.0]), forward_vec)
        right_vec = right_vec / max(np.linalg.norm(right_vec), 0.001)  # Normalize
        
        # Calculate movement direction based on input and facing direction
        if np.linalg.norm(input_direction) > 0.001:
            move_direction = self.calculate_move_direction(forward_vec, right_vec, input_direction)
            
            # Determine if moving sideways or backward to apply appropriate multipliers
            forward_alignment = np.dot(move_direction, forward_vec)
            
            # Default multiplier
            direction_multiplier = 1.0
            
            # Check if moving backward
            if forward_alignment < -0.3:  # More than ~17 degrees backward
                direction_multiplier = self.backward_speed_multiplier
            # Check if strafing
            elif abs(forward_alignment) < 0.7:  # More than ~45 degrees to the side
                direction_multiplier = self.strafe_speed_multiplier
                
            # Apply sprint/crouch modifiers
            if is_sprinting:
                direction_multiplier *= self.sprint_multiplier
            elif is_crouching:
                direction_multiplier *= self.crouch_multiplier
                
            # Scale max speed by appropriate multiplier
            current_max_speed = self.max_speed * direction_multiplier
            
            # Calculate desired velocity
            desired_velocity = move_direction * current_max_speed
            
            # Reduce acceleration in air if needed
            acceleration_modifier = 1.0
            if not obj.get('is_grounded', True):
                acceleration_modifier = self.air_control
                
            # Calculate acceleration force
            current_velocity_horizontal = np.array([obj['velocity'][0], 0.0, obj['velocity'][2]])
            desired_velocity_horizontal = np.array([desired_velocity[0], 0.0, desired_velocity[2]])
            
            # Calculate acceleration needed to reach desired velocity
            acceleration_vector = (desired_velocity_horizontal - current_velocity_horizontal) / delta_time
            
            # Limit acceleration magnitude
            accel_magnitude = np.linalg.norm(acceleration_vector)
            if accel_magnitude > self.acceleration * acceleration_modifier:
                acceleration_vector = acceleration_vector * (self.acceleration * acceleration_modifier / accel_magnitude)
                
            # Calculate force from acceleration: F = ma
            force = acceleration_vector * obj.get('mass', 1.0)
            
            # Apply force to update velocity
            new_velocity = self.motion.apply_force(
                obj.get('mass', 1.0),
                obj['velocity'],
                force,
                delta_time
            )
            
            # Keep vertical velocity component unchanged
            new_velocity[1] = obj['velocity'][1]
            
            updated_obj['velocity'] = new_velocity
        else:
            # No input, decelerate to stop horizontal movement
            current_velocity_horizontal = np.array([obj['velocity'][0], 0.0, obj['velocity'][2]])
            speed = np.linalg.norm(current_velocity_horizontal)
            
            if speed > 0.001:
                # Calculate deceleration direction (opposite to movement)
                deceleration_direction = -current_velocity_horizontal / speed
                
                # Calculate deceleration force
                deceleration = self.deceleration
                if not obj.get('is_grounded', True):
                    deceleration *= self.air_control
                    
                # Calculate force from deceleration: F = ma
                force = deceleration_direction * deceleration * obj.get('mass', 1.0)
                
                # Apply force to update velocity
                new_velocity = self.motion.apply_force(
                    obj.get('mass', 1.0),
                    obj['velocity'],
                    force,
                    delta_time
                )
                
                # Keep vertical velocity component unchanged
                new_velocity[1] = obj['velocity'][1]
                
                updated_obj['velocity'] = new_velocity
        
        return updated_obj
    
    def process_jump(self, obj: Dict[str, Any], jump_force: float) -> Dict[str, Any]:
        """
        Make an object jump with the specified force.
        
        Args:
            obj: Object data containing position, velocity, etc.
            jump_force: Force of the jump (higher = higher jump)
            
        Returns:
            Updated object data
        """
        # Make a copy to avoid modifying the original
        updated_obj = obj.copy()
        
        # Only allow jumping when grounded
        if obj.get('is_grounded', False):
            # Create vertical impulse vector
            jump_impulse = np.array([0.0, jump_force, 0.0])
            
            # Apply impulse to get new velocity
            updated_obj['velocity'] = self.motion.apply_impulse(
                obj.get('mass', 1.0),
                obj['velocity'],
                jump_impulse
            )
            
            # Mark as no longer grounded
            updated_obj['is_grounded'] = False
            
        return updated_obj
    
    def process_dash(self, obj: Dict[str, Any], dash_direction: np.ndarray, 
                    dash_force: float) -> Dict[str, Any]:
        """
        Make an object dash in the specified direction.
        
        Args:
            obj: Object data containing position, velocity, etc.
            dash_direction: Direction to dash in (normalized)
            dash_force: Force of the dash
            
        Returns:
            Updated object data
        """
        # Make a copy to avoid modifying the original
        updated_obj = obj.copy()
        
        # Normalize direction if needed
        magnitude = np.linalg.norm(dash_direction)
        if magnitude > 0.001:
            normalized_direction = dash_direction / magnitude
            
            # Create dash impulse vector
            dash_impulse = normalized_direction * dash_force
            
            # Apply impulse to get new velocity
            updated_obj['velocity'] = self.motion.apply_impulse(
                obj.get('mass', 1.0),
                obj['velocity'],
                dash_impulse
            )
            
        return updated_obj


class MotionPhysicsSystem:
    """
    Main system that updates all motion physics in the game.
    Processes movement, gravity, friction, and other forces.
    """
    
    def __init__(self):
        """Initialize the motion physics system."""
        self.motion = Motion()
        self.omni_movement = OmniMovement(self.motion)
        
    def update(self, game_objects: Dict[int, Dict], delta_time: float) -> Dict[int, Dict]:
        """
        Update physics for all game objects.
        
        Args:
            game_objects: Dictionary mapping object IDs to object data
            delta_time: Time step in seconds
            
        Returns:
            Updated game objects with new positions and velocities
        """
        # Make a copy to avoid modifying while iterating
        updated_objects = {}
        
        for obj_id, obj in game_objects.items():
            updated_obj = obj.copy()
            
            # Skip objects that don't have physics
            if not obj.get('has_physics', True):
                updated_objects[obj_id] = updated_obj
                continue
                
            # Process standard motion physics
            updated_obj = self.motion.process_object_motion(updated_obj, delta_time)
            
            # Process player/AI controlled omni-movement if applicable
            if obj.get('has_controller', False) and 'input_direction' in obj:
                updated_obj = self.omni_movement.apply_movement_input(
                    updated_obj,
                    obj['input_direction'],
                    delta_time,
                    obj.get('is_sprinting', False),
                    obj.get('is_crouching', False)
                )
            
            # Store the updated object
            updated_objects[obj_id] = updated_obj
            
        return updated_objects