import math
from core.eventManager import EventManager
from core.timeManager import TimeManager
from physics.raycast import raycast
from characters.players import Player
from characters.enemies import Enemy
from configs.weaponData import get_weapon_config
from scripts.inputManager import InputManager


class AimAssist:
    def __init__(self, player, config=None):
        """
        Initialize the aim assist system for a specific player.
        
        Args:
            player: Player object that receives aim assistance
            config: Optional custom configuration dictionary
        """
        self.player = player
        self.event_manager = EventManager()
        self.time_manager = TimeManager()
        self.input_manager = InputManager()
        
        # Default configuration
        self.config = {
            "enabled": True,
            "assist_strength": 0.4,  # 0.0 to 1.0
            "assist_range": 30.0,    # Max distance in units to apply assist
            "fov_scale": 15.0,       # Field of view for target detection (degrees)
            "sticky_aim_strength": 0.3,  # How much aim slows when passing over targets
            "bullet_magnetism": 0.2,  # How much bullets curve toward targets
            "friction_strength": 0.35,  # Slow-down when aim passes over target
            "assist_mode": "adaptive",  # adaptive, standard, minimal, or disabled
            "target_priority": ["head", "torso", "limbs"],
            "platform_compensation": 1.0,  # Higher for controller/mobile
            "lerp_speed": 0.15,       # Speed of aim correction
            "detection_filter": ["players", "enemies"],  # What entities can be assisted to
            "accuracy_threshold": 0.7,  # Player accuracy threshold for adaptive mode
            "slowdown_timeout": 0.3,   # Time in seconds for sticky aim to remain active
            "debug_visualization": False,  # Show assist visualization for debugging
        }
        
        # Override defaults with custom config if provided
        if config:
            self.config.update(config)
            
        # State variables
        self.current_targets = []
        self.primary_target = None
        self.last_assist_time = 0
        self.assist_active = False
        self.player_stats = {"accuracy": 0.5, "skill_rating": 1000}
        
        # Register events
        self.event_manager.register("weapon_fired", self.on_weapon_fired)
        self.event_manager.register("player_skill_updated", self.on_player_skill_updated)
        self.event_manager.register("settings_changed", self.on_settings_changed)
    
    def update(self, delta_time):
        """
        Update the aim assist system. Called every frame.
        
        Args:
            delta_time: Time elapsed since the last frame
        """
        if not self.config["enabled"]:
            return
            
        # Adapt assist strength based on player skill if in adaptive mode
        if self.config["assist_mode"] == "adaptive":
            self._adapt_to_player_skill()
        
        # Get potential targets in the player's field of view
        self.current_targets = self._detect_targets()
        
        # Choose the best target to assist to
        self.primary_target = self._select_primary_target()
        
        # Apply aim assistance if we have a valid target
        if self.primary_target:
            self._apply_aim_assistance(delta_time)
            self.last_assist_time = self.time_manager.get_current_time()
            self.assist_active = True
        elif self.assist_active:
            # Check if assist should be deactivated (timeout)
            current_time = self.time_manager.get_current_time()
            if current_time - self.last_assist_time > self.config["slowdown_timeout"]:
                self.assist_active = False
        
        # Debug visualization
        if self.config["debug_visualization"]:
            self._draw_debug_info()
    
    def _detect_targets(self):
        """
        Detect potential targets within the player's field of view.
        
        Returns:
            List of potential target objects with additional metadata
        """
        targets = []
        
        # Get player's view direction and position
        player_pos = self.player.get_position()
        player_look_dir = self.player.get_look_direction()
        
        # Get all potential targets from the game world
        potential_targets = self._get_all_targets()
        
        for target in potential_targets:
            # Skip targets that don't match our filter
            if not self._is_valid_target_type(target):
                continue
                
            # Calculate direction to target
            target_pos = target.get_position()
            direction_to_target = self._normalize(self._vector_subtract(target_pos, player_pos))
            
            # Calculate distance to target
            distance = self._vector_distance(player_pos, target_pos)
            
            # Skip targets outside assist range
            if distance > self.config["assist_range"]:
                continue
            
            # Calculate angle between look direction and target direction
            angle = self._angle_between_vectors(player_look_dir, direction_to_target)
            
            # Scale FOV based on distance (narrower FOV for distant targets)
            scaled_fov = self.config["fov_scale"] * (1.0 - (distance / self.config["assist_range"]) * 0.5)
            
            # Skip targets outside the FOV
            if angle > scaled_fov:
                continue
            
            # Check if target is occluded by obstacles
            if not self._has_line_of_sight(player_pos, target_pos):
                continue
            
            # Get target hitbox regions for prioritization
            hitbox_regions = self._get_target_hitbox_regions(target)
            
            # Add target to the list with metadata
            targets.append({
                "entity": target,
                "distance": distance,
                "angle": angle,
                "direction": direction_to_target,
                "hitbox_regions": hitbox_regions
            })
        
        return targets
    
    def _select_primary_target(self):
        """
        Select the best target from the list of current targets.
        
        Returns:
            The best target object or None if no suitable targets
        """
        if not self.current_targets:
            return None
            
        # Weight factors for target selection
        best_target = None
        best_score = -float('inf')
        
        for target in self.current_targets:
            # Calculate score based on multiple factors
            angle_score = 1.0 - (target["angle"] / self.config["fov_scale"])
            distance_score = 1.0 - (target["distance"] / self.config["assist_range"])
            
            # Apply region priority weights
            region_score = 0
            for region, data in target["hitbox_regions"].items():
                if region in self.config["target_priority"]:
                    priority_idx = self.config["target_priority"].index(region)
                    region_weight = 1.0 - (priority_idx / len(self.config["target_priority"]))
                    region_score = max(region_score, region_weight * data["visibility"])
            
            # Combined weighted score
            score = (angle_score * 0.5) + (distance_score * 0.3) + (region_score * 0.2)
            
            # Additional factor: prioritize targets the player has damaged recently
            if hasattr(target["entity"], "last_damaged_by") and target["entity"].last_damaged_by == self.player.id:
                score += 0.15
                
            # Check if this is the best target so far
            if score > best_score:
                best_score = score
                best_target = target
        
        return best_target
    
    def _apply_aim_assistance(self, delta_time):
        """
        Apply aim assistance effects toward the primary target.
        
        Args:
            delta_time: Time elapsed since the last frame
        """
        if not self.primary_target:
            return
            
        # Get current input values
        current_aim = self.input_manager.get_aim_input(self.player.id)
        
        # Calculate ideal aim direction to target
        player_pos = self.player.get_position()
        target_pos = self._get_target_aim_point()
        ideal_direction = self._normalize(self._vector_subtract(target_pos, player_pos))
        
        # Current look direction
        current_direction = self.player.get_look_direction()
        
        # Calculate rotations needed to align with target
        yaw_correction, pitch_correction = self._calculate_aim_corrections(current_direction, ideal_direction)
        
        # Scale corrections by assist strength and distance
        distance_factor = 1.0 - (self.primary_target["distance"] / self.config["assist_range"])
        strength = self.config["assist_strength"] * distance_factor * self.config["platform_compensation"]
        
        # Apply sticky-aim slowdown when passing over target
        if self._is_aiming_over_target():
            friction = self.config["friction_strength"] * strength
            current_aim = (current_aim[0] * (1.0 - friction), current_aim[1] * (1.0 - friction))
        
        # Apply actual correction with smoothing (lerp)
        correction_factor = min(1.0, self.config["lerp_speed"] * delta_time * 60.0)
        
        # Only apply correction if player is actively aiming
        if abs(current_aim[0]) > 0.01 or abs(current_aim[1]) > 0.01:
            corrected_aim = (
                current_aim[0] + yaw_correction * strength * correction_factor,
                current_aim[1] + pitch_correction * strength * correction_factor
            )
            
            # Apply the corrected input
            self.input_manager.set_aim_input(self.player.id, corrected_aim)
    
    def apply_bullet_magnetism(self, shot_direction):
        """
        Apply bullet magnetism effect for shots.
        
        Args:
            shot_direction: Original normalized direction vector of the shot
            
        Returns:
            Modified direction vector with bullet magnetism applied
        """
        if not self.config["enabled"] or not self.primary_target or self.config["bullet_magnetism"] <= 0:
            return shot_direction
            
        # Get current weapon properties that might affect magnetism
        weapon_config = self._get_current_weapon_config()
        weapon_magnetism_modifier = weapon_config.get("magnetism_modifier", 1.0)
        
        # Calculate ideal direction to target
        player_pos = self.player.get_position()
        target_pos = self._get_target_aim_point()
        ideal_direction = self._normalize(self._vector_subtract(target_pos, player_pos))
        
        # Calculate angle between current shot and ideal direction
        angle = self._angle_between_vectors(shot_direction, ideal_direction)
        
        # Maximum angle that can be affected by magnetism (in degrees)
        max_magnetism_angle = 5.0
        
        # Only apply magnetism if within reasonable angle
        if angle <= max_magnetism_angle:
            # Calculate magnetism strength based on angle
            magnetism_strength = self.config["bullet_magnetism"] * weapon_magnetism_modifier
            magnetism_strength *= (1.0 - (angle / max_magnetism_angle))
            
            # Apply magnetism via lerp
            return self._vector_lerp(shot_direction, ideal_direction, magnetism_strength)
        
        return shot_direction
    
    def on_weapon_fired(self, event_data):
        """
        Event handler for weapon fired events.
        
        Args:
            event_data: Data associated with the weapon fired event
        """
        if event_data["player_id"] != self.player.id:
            return
            
        # Track hit/miss for accuracy calculation
        hit = event_data.get("hit", False)
        self._update_accuracy_stats(hit)
    
    def on_player_skill_updated(self, event_data):
        """
        Event handler for player skill rating updates.
        
        Args:
            event_data: Data associated with the skill update event
        """
        if event_data["player_id"] != self.player.id:
            return
            
        # Update stored player stats
        if "accuracy" in event_data:
            self.player_stats["accuracy"] = event_data["accuracy"]
        if "skill_rating" in event_data:
            self.player_stats["skill_rating"] = event_data["skill_rating"]
    
    def on_settings_changed(self, event_data):
        """
        Event handler for game settings changes.
        
        Args:
            event_data: Data associated with the settings change event
        """
        if "aim_assist" in event_data:
            assist_settings = event_data["aim_assist"]
            for key, value in assist_settings.items():
                if key in self.config:
                    self.config[key] = value
    
    def _adapt_to_player_skill(self):
        """Adjust aim assist parameters based on player skill level."""
        # Base scaling factors
        accuracy = self.player_stats["accuracy"]
        skill_rating = self.player_stats["skill_rating"]
        
        # Normalize skill rating (assuming 1000 is average)
        normalized_skill = min(2.0, max(0.5, skill_rating / 1000))
        
        # Adjust assist strength inversely proportional to skill
        base_strength = self.config["assist_strength"]
        adjusted_strength = base_strength * (1.0 - (accuracy - 0.5))
        adjusted_strength = max(0.1, min(base_strength, adjusted_strength))
        
        # Apply adjustments temporarily (don't modify original config)
        self.config["assist_strength"] = adjusted_strength
        self.config["bullet_magnetism"] *= (1.0 - (normalized_skill - 0.5) * 0.5)
        self.config["friction_strength"] *= (1.0 - (normalized_skill - 0.5) * 0.3)
    
    def _get_all_targets(self):
        """
        Get all potential targets from the game world.
        
        Returns:
            List of potential target entities
        """
        # This would typically query the game's entity system
        # For simplicity, we'll assume there's a method to get all relevant entities
        entities = []
        
        # Add players if in detection filter
        if "players" in self.config["detection_filter"]:
            # Exclude the current player
            players = [p for p in Player.get_all_active() if p.id != self.player.id]
            # Filter for enemy players only
            if hasattr(self.player, "team"):
                players = [p for p in players if p.team != self.player.team]
            entities.extend(players)
        
        # Add enemies if in detection filter
        if "enemies" in self.config["detection_filter"]:
            entities.extend(Enemy.get_all_active())
        
        return entities
    
    def _is_valid_target_type(self, target):
        """
        Check if the target entity is of a valid type for aim assist.
        
        Args:
            target: Target entity to check
            
        Returns:
            Boolean indicating if target type is valid
        """
        if "players" in self.config["detection_filter"] and isinstance(target, Player):
            return True
        if "enemies" in self.config["detection_filter"] and isinstance(target, Enemy):
            return True
        return False
    
    def _has_line_of_sight(self, from_pos, to_pos):
        """
        Check if there's a clear line of sight between two positions.
        
        Args:
            from_pos: Starting position
            to_pos: Target position
            
        Returns:
            Boolean indicating if there's clear line of sight
        """
        # Perform a raycast to check for obstacles
        hit_info = raycast(from_pos, to_pos)
        
        # Check if the raycast hit the intended target or was blocked
        return not hit_info["blocked"]
    
    def _get_target_hitbox_regions(self, target):
        """
        Get the hitbox regions of a target with visibility information.
        
        Args:
            target: Target entity
            
        Returns:
            Dictionary of hitbox regions with visibility data
        """
        # This would typically query the target's hitbox system
        # For simplicity, we'll return a sample structure
        if hasattr(target, "get_hitbox_regions"):
            return target.get_hitbox_regions()
        
        # Default hitbox regions if not available on entity
        return {
            "head": {"position": None, "visibility": 1.0},
            "torso": {"position": None, "visibility": 1.0},
            "limbs": {"position": None, "visibility": 1.0}
        }
    
    def _get_target_aim_point(self):
        """
        Get the optimal aim point on the primary target.
        
        Returns:
            Position vector for ideal aim point
        """
        if not self.primary_target:
            return None
            
        # Try to aim at the highest priority hitbox region that's visible
        target = self.primary_target
        for region in self.config["target_priority"]:
            if region in target["hitbox_regions"]:
                region_data = target["hitbox_regions"][region]
                if region_data["visibility"] > 0.5 and region_data["position"]:
                    return region_data["position"]
        
        # Fall back to entity position if no hitbox is suitable
        return self.primary_target["entity"].get_position()
    
    def _is_aiming_over_target(self):
        """
        Determine if the player is currently aiming over the target.
        
        Returns:
            Boolean indicating if aiming over target
        """
        if not self.primary_target:
            return False
            
        # Calculate ray from player's view
        player_pos = self.player.get_position()
        look_dir = self.player.get_look_direction()
        
        # Cast a ray along the look direction
        hit_info = raycast(player_pos, look_dir, max_distance=self.config["assist_range"])
        
        # Check if ray hit the primary target
        if hit_info["hit"] and hit_info["entity"] == self.primary_target["entity"]:
            return True
            
        return False
    
    def _calculate_aim_corrections(self, current_dir, ideal_dir):
        """
        Calculate yaw and pitch corrections to align with target.
        
        Args:
            current_dir: Current normalized look direction
            ideal_dir: Ideal normalized direction to target
            
        Returns:
            Tuple of (yaw_correction, pitch_correction)
        """
        # Extract yaw and pitch angles from direction vectors
        current_yaw = math.atan2(current_dir[0], current_dir[2])
        current_pitch = math.asin(-current_dir[1])
        
        ideal_yaw = math.atan2(ideal_dir[0], ideal_dir[2])
        ideal_pitch = math.asin(-ideal_dir[1])
        
        # Calculate shortest angle differences
        yaw_diff = self._normalize_angle(ideal_yaw - current_yaw)
        pitch_diff = self._normalize_angle(ideal_pitch - current_pitch)
        
        return yaw_diff, pitch_diff
    
    def _update_accuracy_stats(self, hit):
        """
        Update player accuracy statistics.
        
        Args:
            hit: Boolean indicating if the shot hit a target
        """
        # Simple exponential moving average for accuracy
        decay_factor = 0.05  # How quickly new shots affect the average
        self.player_stats["accuracy"] = (self.player_stats["accuracy"] * (1 - decay_factor) + 
                                        (1.0 if hit else 0.0) * decay_factor)
    
    def _get_current_weapon_config(self):
        """
        Get the configuration of the player's current weapon.
        
        Returns:
            Dictionary with weapon configuration
        """
        if hasattr(self.player, "current_weapon_id"):
            return get_weapon_config(self.player.current_weapon_id)
        return {"magnetism_modifier": 1.0}
    
    def _draw_debug_info(self):
        """Draw debug visualization for aim assist."""
        # This would use the game's debug drawing system
        # Implementation depends on the game engine
        pass
    
    # ===== Vector Math Utility Methods =====
    
    def _normalize(self, vector):
        """Normalize a vector to unit length."""
        magnitude = math.sqrt(sum(x*x for x in vector))
        if magnitude < 0.0001:
            return vector  # Avoid division by zero
        return tuple(x/magnitude for x in vector)
    
    def _vector_subtract(self, v1, v2):
        """Subtract vector v2 from v1."""
        return tuple(a - b for a, b in zip(v1, v2))
    
    def _vector_distance(self, v1, v2):
        """Calculate distance between two vectors."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
    
    def _angle_between_vectors(self, v1, v2):
        """Calculate angle in degrees between two vectors."""
        v1_norm = self._normalize(v1)
        v2_norm = self._normalize(v2)
        dot_product = sum(a * b for a, b in zip(v1_norm, v2_norm))
        # Clamp dot product to avoid floating point errors
        dot_product = max(-1.0, min(1.0, dot_product))
        angle_rad = math.acos(dot_product)
        return math.degrees(angle_rad)
    
    def _normalize_angle(self, angle):
        """Normalize an angle to the range [-π, π]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def _vector_lerp(self, v1, v2, t):
        """Linear interpolation between two vectors."""
        t = max(0.0, min(1.0, t))  # Clamp t to [0, 1]
        return tuple(a + (b - a) * t for a, b in zip(v1, v2))