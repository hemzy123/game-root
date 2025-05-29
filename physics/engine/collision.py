import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

class CollisionDetector:
    """
    Handles detection of collisions between various types of game objects.
    Supports sphere-sphere, sphere-box, box-box, and ray-object collisions.
    """
    
    @staticmethod
    def check_sphere_sphere(pos1: np.ndarray, radius1: float, 
                           pos2: np.ndarray, radius2: float) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Check for collision between two spheres.
        
        Args:
            pos1: Center position of first sphere (x, y, z)
            radius1: Radius of first sphere
            pos2: Center position of second sphere (x, y, z)
            radius2: Radius of second sphere
            
        Returns:
            Tuple containing:
            - Boolean indicating if collision occurred
            - Optional collision normal (unit vector) if collision occurred, None otherwise
        """
        direction = pos2 - pos1
        distance_squared = np.sum(direction * direction)
        min_distance = radius1 + radius2
        
        if distance_squared < min_distance * min_distance:
            # Collision detected
            if distance_squared > 0.0001:  # Avoid division by zero
                normal = direction / math.sqrt(distance_squared)
                return True, normal
            else:
                # Objects are at the same position, use default up vector
                return True, np.array([0, 1, 0])
        
        return False, None
    
    @staticmethod
    def check_sphere_box(sphere_pos: np.ndarray, sphere_radius: float,
                        box_pos: np.ndarray, box_half_size: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Check for collision between a sphere and an axis-aligned box.
        
        Args:
            sphere_pos: Center position of sphere (x, y, z)
            sphere_radius: Radius of sphere
            box_pos: Center position of box (x, y, z)
            box_half_size: Half size of box in each dimension (x, y, z)
            
        Returns:
            Tuple containing:
            - Boolean indicating if collision occurred
            - Optional collision normal (unit vector) if collision occurred, None otherwise
        """
        # Calculate closest point on box to sphere center
        closest_point = np.array([
            max(box_pos[0] - box_half_size[0], min(sphere_pos[0], box_pos[0] + box_half_size[0])),
            max(box_pos[1] - box_half_size[1], min(sphere_pos[1], box_pos[1] + box_half_size[1])),
            max(box_pos[2] - box_half_size[2], min(sphere_pos[2], box_pos[2] + box_half_size[2]))
        ])
        
        # Calculate distance between closest point and sphere center
        direction = sphere_pos - closest_point
        distance_squared = np.sum(direction * direction)
        
        if distance_squared < sphere_radius * sphere_radius:
            # Collision detected
            if distance_squared > 0.0001:  # Avoid division by zero
                normal = direction / math.sqrt(distance_squared)
                return True, normal
            else:
                # Find the face normal for the collision
                distances = [
                    abs(sphere_pos[0] - (box_pos[0] - box_half_size[0])),  # Left face
                    abs(sphere_pos[0] - (box_pos[0] + box_half_size[0])),  # Right face
                    abs(sphere_pos[1] - (box_pos[1] - box_half_size[1])),  # Bottom face
                    abs(sphere_pos[1] - (box_pos[1] + box_half_size[1])),  # Top face
                    abs(sphere_pos[2] - (box_pos[2] - box_half_size[2])),  # Back face
                    abs(sphere_pos[2] - (box_pos[2] + box_half_size[2]))   # Front face
                ]
                min_index = distances.index(min(distances))
                
                # Map index to normal
                normals = [
                    np.array([-1, 0, 0]),  # Left
                    np.array([1, 0, 0]),   # Right
                    np.array([0, -1, 0]),  # Bottom
                    np.array([0, 1, 0]),   # Top
                    np.array([0, 0, -1]),  # Back
                    np.array([0, 0, 1])    # Front
                ]
                return True, normals[min_index]
        
        return False, None
    
    @staticmethod
    def check_box_box(pos1: np.ndarray, half_size1: np.ndarray,
                     pos2: np.ndarray, half_size2: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Check for collision between two axis-aligned boxes.
        
        Args:
            pos1: Center position of first box (x, y, z)
            half_size1: Half size of first box in each dimension (x, y, z)
            pos2: Center position of second box (x, y, z)
            half_size2: Half size of second box in each dimension (x, y, z)
            
        Returns:
            Tuple containing:
            - Boolean indicating if collision occurred
            - Optional collision normal (unit vector) if collision occurred, None otherwise
        """
        # Check for overlap along each axis
        x_overlap = (pos1[0] + half_size1[0] >= pos2[0] - half_size2[0] and
                    pos2[0] + half_size2[0] >= pos1[0] - half_size1[0])
        y_overlap = (pos1[1] + half_size1[1] >= pos2[1] - half_size2[1] and
                    pos2[1] + half_size2[1] >= pos1[1] - half_size1[1])
        z_overlap = (pos1[2] + half_size1[2] >= pos2[2] - half_size2[2] and
                    pos2[2] + half_size2[2] >= pos1[2] - half_size1[2])
        
        if x_overlap and y_overlap and z_overlap:
            # Calculate penetration depth along each axis
            x_depth = min(pos1[0] + half_size1[0] - (pos2[0] - half_size2[0]),
                         pos2[0] + half_size2[0] - (pos1[0] - half_size1[0]))
            y_depth = min(pos1[1] + half_size1[1] - (pos2[1] - half_size2[1]),
                         pos2[1] + half_size2[1] - (pos1[1] - half_size1[1]))
            z_depth = min(pos1[2] + half_size1[2] - (pos2[2] - half_size2[2]),
                         pos2[2] + half_size2[2] - (pos1[2] - half_size1[2]))
            
            # Find the axis with minimum penetration
            if x_depth <= y_depth and x_depth <= z_depth:
                normal = np.array([1, 0, 0] if pos1[0] < pos2[0] else [-1, 0, 0])
            elif y_depth <= x_depth and y_depth <= z_depth:
                normal = np.array([0, 1, 0] if pos1[1] < pos2[1] else [0, -1, 0])
            else:
                normal = np.array([0, 0, 1] if pos1[2] < pos2[2] else [0, 0, -1])
                
            return True, normal
        
        return False, None
    
    @staticmethod
    def ray_cast(ray_origin: np.ndarray, ray_direction: np.ndarray, 
                max_distance: float, objects: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Cast a ray and find the first object it hits.
        
        Args:
            ray_origin: Starting position of ray (x, y, z)
            ray_direction: Normalized direction vector of ray
            max_distance: Maximum distance to check
            objects: List of objects to check for intersection
                     Each object needs a 'type' field ('sphere' or 'box')
                     and appropriate position and size parameters
                     
        Returns:
            Tuple containing:
            - Boolean indicating if hit occurred
            - Optional dict with hit information (object, distance, point, normal)
        """
        closest_hit = None
        closest_distance = max_distance
        
        for obj in objects:
            hit = False
            hit_distance = None
            hit_normal = None
            
            if obj['type'] == 'sphere':
                # Ray-sphere intersection
                sphere_pos = obj['position']
                sphere_radius = obj['radius']
                
                # Vector from ray origin to sphere center
                offset = sphere_pos - ray_origin
                
                # Project offset onto ray direction to find closest point on ray to sphere center
                projected_distance = np.dot(offset, ray_direction)
                
                if projected_distance < 0:
                    # Sphere is behind ray origin
                    continue
                
                # Squared distance from sphere center to ray
                closest_point = ray_origin + ray_direction * projected_distance
                closest_point_dist_squared = np.sum((closest_point - sphere_pos) ** 2)
                
                # Check if ray passes through sphere
                if closest_point_dist_squared > sphere_radius * sphere_radius:
                    continue
                
                # Calculate actual intersection distance
                half_chord = math.sqrt(sphere_radius * sphere_radius - closest_point_dist_squared)
                hit_distance = projected_distance - half_chord
                
                if hit_distance < closest_distance:
                    hit = True
                    hit_point = ray_origin + ray_direction * hit_distance
                    hit_normal = (hit_point - sphere_pos) / sphere_radius
            
            elif obj['type'] == 'box':
                # Ray-box intersection (AABB)
                box_pos = obj['position']
                box_half_size = obj['half_size']
                
                # Calculate box bounds
                min_bounds = box_pos - box_half_size
                max_bounds = box_pos + box_half_size
                
                # Initialize parameters for slab method
                t_min = -float('inf')
                t_max = float('inf')
                hit_normal_axis = 0
                hit_normal_sign = 1
                
                # Check intersection with each slab
                for i in range(3):
                    if abs(ray_direction[i]) < 1e-6:
                        # Ray is parallel to slab, check if origin is within slab
                        if ray_origin[i] < min_bounds[i] or ray_origin[i] > max_bounds[i]:
                            # Ray misses the box
                            break
                    else:
                        # Calculate intersection times
                        t1 = (min_bounds[i] - ray_origin[i]) / ray_direction[i]
                        t2 = (max_bounds[i] - ray_origin[i]) / ray_direction[i]
                        
                        # Ensure t1 < t2
                        if t1 > t2:
                            t1, t2 = t2, t1
                            sign = -1
                        else:
                            sign = 1
                        
                        # Update t_min and t_max
                        if t1 > t_min:
                            t_min = t1
                            hit_normal_axis = i
                            hit_normal_sign = -sign
                        
                        t_max = min(t_max, t2)
                        
                        if t_min > t_max:
                            # Ray misses the box
                            break
                else:
                    # If we get here, the ray hits the box
                    hit_distance = t_min if t_min > 0 else t_max
                    
                    if hit_distance > 0 and hit_distance < closest_distance:
                        hit = True
                        hit_normal = np.zeros(3)
                        hit_normal[hit_normal_axis] = hit_normal_sign
            
            if hit and hit_distance < closest_distance:
                closest_distance = hit_distance
                hit_point = ray_origin + ray_direction * hit_distance
                closest_hit = {
                    'object': obj,
                    'distance': hit_distance,
                    'point': hit_point,
                    'normal': hit_normal
                }
        
        return closest_hit is not None, closest_hit


class CollisionResolver:
    """
    Resolves collisions between objects by applying appropriate physics responses.
    """
    
    @staticmethod
    def resolve_sphere_collision(pos1: np.ndarray, velocity1: np.ndarray, mass1: float, radius1: float,
                                pos2: np.ndarray, velocity2: np.ndarray, mass2: float, radius2: float,
                                restitution: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Resolve collision between two spheres using conservation of momentum and energy.
        
        Args:
            pos1: Position of first sphere
            velocity1: Velocity of first sphere
            mass1: Mass of first sphere
            radius1: Radius of first sphere
            pos2: Position of second sphere
            velocity2: Velocity of second sphere
            mass2: Mass of second sphere
            radius2: Radius of second sphere
            restitution: Coefficient of restitution (0 = inelastic, 1 = elastic)
            
        Returns:
            Tuple of new velocities for both spheres
        """
        # Calculate normal vector
        normal = pos1 - pos2
        distance = np.linalg.norm(normal)
        
        # Avoid division by zero
        if distance < 0.0001:
            return velocity1, velocity2
            
        normal = normal / distance
        
        # Calculate relative velocity
        rel_velocity = velocity1 - velocity2
        
        # Check if objects are moving apart
        vel_along_normal = np.dot(rel_velocity, normal)
        if vel_along_normal > 0:
            return velocity1, velocity2
        
        # Calculate impulse
        j = -(1 + restitution) * vel_along_normal
        j /= (1 / mass1) + (1 / mass2)
        
        # Apply impulse
        new_velocity1 = velocity1 + (j / mass1) * normal
        new_velocity2 = velocity2 - (j / mass2) * normal
        
        return new_velocity1, new_velocity2
    
    @staticmethod
    def resolve_penetration(pos1: np.ndarray, radius1: float, 
                           pos2: np.ndarray, radius2: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Resolve penetration between two spheres by moving them apart.
        
        Args:
            pos1: Position of first sphere
            radius1: Radius of first sphere
            pos2: Position of second sphere
            radius2: Radius of second sphere
            
        Returns:
            Tuple of new positions for both spheres
        """
        # Calculate penetration vector
        direction = pos1 - pos2
        distance = np.linalg.norm(direction)
        
        # Avoid division by zero
        if distance < 0.0001:
            # If objects are at the same position, push in a random direction
            direction = np.array([1, 0, 0])
            distance = 1.0
        else:
            direction = direction / distance
        
        # Calculate penetration depth
        penetration = radius1 + radius2 - distance
        
        if penetration <= 0:
            return pos1, pos2
        
        # Calculate displacement based on mass ratio (assuming equal mass for simplicity)
        displacement = direction * penetration / 2
        
        new_pos1 = pos1 + displacement
        new_pos2 = pos2 - displacement
        
        return new_pos1, new_pos2


class CollisionManager:
    """
    Main collision management class for the game physics engine.
    Handles detection and resolution of collisions between game objects.
    """
    
    def __init__(self):
        self.detector = CollisionDetector()
        self.resolver = CollisionResolver()
        self.collision_layers = {}  # For collision filtering
        
    def add_to_layer(self, object_id: int, layer_name: str):
        """
        Add an object to a collision layer for filtering.
        
        Args:
            object_id: Unique identifier for the object
            layer_name: Name of the layer to add the object to
        """
        if layer_name not in self.collision_layers:
            self.collision_layers[layer_name] = set()
        
        self.collision_layers[layer_name].add(object_id)
    
    def remove_from_layer(self, object_id: int, layer_name: str):
        """
        Remove an object from a collision layer.
        
        Args:
            object_id: Unique identifier for the object
            layer_name: Name of the layer to remove the object from
        """
        if layer_name in self.collision_layers:
            self.collision_layers[layer_name].discard(object_id)
    
    def should_check_collision(self, obj1_id: int, obj2_id: int, collision_matrix: Dict[str, List[str]]) -> bool:
        """
        Determine if collision should be checked between two objects based on their layers.
        
        Args:
            obj1_id: ID of first object
            obj2_id: ID of second object
            collision_matrix: Dictionary mapping layer names to lists of layers they collide with
            
        Returns:
            Boolean indicating if collision should be checked
        """
        # Find which layers each object belongs to
        obj1_layers = []
        obj2_layers = []
        
        for layer_name, objects in self.collision_layers.items():
            if obj1_id in objects:
                obj1_layers.append(layer_name)
            if obj2_id in objects:
                obj2_layers.append(layer_name)
        
        # Check if any layer of obj1 collides with any layer of obj2
        for layer1 in obj1_layers:
            if layer1 in collision_matrix:
                for layer2 in obj2_layers:
                    if layer2 in collision_matrix[layer1]:
                        return True
        
        return False
    
    def process_collisions(self, game_objects: Dict[int, Dict], collision_matrix: Dict[str, List[str]], 
                          restitution: float = 0.5) -> Dict[int, Dict]:
        """
        Process all collisions between game objects.
        
        Args:
            game_objects: Dictionary mapping object IDs to object data
                         Each object needs:
                         - 'shape': 'sphere' or 'box'
                         - 'position': np.ndarray position
                         - 'velocity': np.ndarray velocity
                         - 'mass': float mass
                         - Shape-specific parameters (radius for sphere, half_size for box)
            collision_matrix: Dictionary defining which layers collide with each other
            restitution: Global coefficient of restitution
            
        Returns:
            Updated game_objects dictionary with resolved collisions
        """
        # Make a copy to avoid modifying while iterating
        updated_objects = game_objects.copy()
        
        # Process collisions between pairs of objects
        object_ids = list(game_objects.keys())
        for i in range(len(object_ids) - 1):
            for j in range(i + 1, len(object_ids)):
                obj1_id = object_ids[i]
                obj2_id = object_ids[j]
                
                # Check if these objects should collide based on layers
                if not self.should_check_collision(obj1_id, obj2_id, collision_matrix):
                    continue
                
                obj1 = game_objects[obj1_id]
                obj2 = game_objects[obj2_id]
                
                collision_detected = False
                collision_normal = None
                
                # Detect collision based on shape types
                if obj1['shape'] == 'sphere' and obj2['shape'] == 'sphere':
                    collision_detected, collision_normal = CollisionDetector.check_sphere_sphere(
                        obj1['position'], obj1['radius'],
                        obj2['position'], obj2['radius']
                    )
                elif obj1['shape'] == 'box' and obj2['shape'] == 'box':
                    collision_detected, collision_normal = CollisionDetector.check_box_box(
                        obj1['position'], obj1['half_size'],
                        obj2['position'], obj2['half_size']
                    )
                elif obj1['shape'] == 'sphere' and obj2['shape'] == 'box':
                    collision_detected, collision_normal = CollisionDetector.check_sphere_box(
                        obj1['position'], obj1['radius'],
                        obj2['position'], obj2['half_size']
                    )
                    if collision_detected and collision_normal is not None:
                        collision_normal = -collision_normal  # Reverse normal for correct resolution
                elif obj1['shape'] == 'box' and obj2['shape'] == 'sphere':
                    collision_detected, collision_normal = CollisionDetector.check_sphere_box(
                        obj2['position'], obj2['radius'],
                        obj1['position'], obj1['half_size']
                    )
                
                if collision_detected and collision_normal is not None:
                    # Resolve collision if detected
                    if obj1['shape'] == 'sphere' and obj2['shape'] == 'sphere':
                        # Resolve velocity for sphere-sphere collision
                        new_vel1, new_vel2 = CollisionResolver.resolve_sphere_collision(
                            obj1['position'], obj1['velocity'], obj1['mass'], obj1['radius'],
                            obj2['position'], obj2['velocity'], obj2['mass'], obj2['radius'],
                            restitution
                        )
                        
                        updated_objects[obj1_id]['velocity'] = new_vel1
                        updated_objects[obj2_id]['velocity'] = new_vel2
                        
                        # Resolve penetration for sphere-sphere collision
                        new_pos1, new_pos2 = CollisionResolver.resolve_penetration(
                            obj1['position'], obj1['radius'],
                            obj2['position'], obj2['radius']
                        )
                        
                        updated_objects[obj1_id]['position'] = new_pos1
                        updated_objects[obj2_id]['position'] = new_pos2
                    else:
                        # For other collision types, apply a simplified impulse resolution
                        # This is a simplified approach for mixed collision types
                        rel_velocity = obj1['velocity'] - obj2['velocity']
                        vel_along_normal = np.dot(rel_velocity, collision_normal)
                        
                        # Skip if objects are moving apart
                        if vel_along_normal > 0:
                            continue
                        
                        # Calculate impulse
                        j = -(1 + restitution) * vel_along_normal
                        j /= (1 / obj1['mass']) + (1 / obj2['mass'])
                        
                        # Apply impulse
                        impulse = j * collision_normal
                        updated_objects[obj1_id]['velocity'] = obj1['velocity'] + impulse / obj1['mass']
                        updated_objects[obj2_id]['velocity'] = obj2['velocity'] - impulse / obj2['mass']
                        
                        # Apply simple position correction to prevent sinking
                        # Determine penetration depth (simplified)
                        penetration = 0.1  # Default small value
                        correction = (penetration * 0.8) * collision_normal / (1/obj1['mass'] + 1/obj2['mass'])
                        
                        updated_objects[obj1_id]['position'] = obj1['position'] + (correction / obj1['mass'])
                        updated_objects[obj2_id]['position'] = obj2['position'] - (correction / obj2['mass'])
        
        return updated_objects