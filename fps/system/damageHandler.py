import random
import math
from core.eventManager import EventManager
from core.timeManager import TimeManager
from physics.raycast import raycast
from characters.players import Player
from characters.enemies import Enemy
from configs.weaponData import get_weapon_config
from fps.gunSystem import GunSystem
from scripts.analytics import AnalyticsTracker


class DamageHandler:
    def __init__(self):
        """Initialize the damage handler system."""
        self.event_manager = EventManager()
        self.time_manager = TimeManager()
        self.analytics = AnalyticsTracker()
        self.gun_system = GunSystem()
        
        # Damage types and their properties
        self.damage_types = {
            "physical": {
                "color": (200, 50, 50),  # RGB for UI indicators
                "sfx": "hit_physical",
                "penetration_factor": 1.0
            },
            "explosive": {
                "color": (255, 140, 0),
                "sfx": "hit_explosive",
                "penetration_factor": 1.5,
                "radius": 3.0  # Explosion radius in meters
            },
            "energy": {
                "color": (50, 150, 255),
                "sfx": "hit_energy",
                "penetration_factor": 0.8,
                "shield_multiplier": 1.5  # Extra damage to shields
            },
            "fire": {
                "color": (255, 70, 0),
                "sfx": "hit_fire",
                "penetration_factor": 0.3,
                "dot_duration": 3.0,  # Damage over time duration in seconds
                "dot_tick_rate": 0.5  # How often DoT applies in seconds
            },
            "cryo": {
                "color": (150, 220, 255),
                "sfx": "hit_cryo",
                "penetration_factor": 0.8,
                "slow_factor": 0.3,  # Movement speed reduction
                "slow_duration": 2.0  # Slow effect duration in seconds
            },
            "poison": {
                "color": (100, 200, 50),
                "sfx": "hit_poison",
                "penetration_factor": 0.5,
                "dot_duration": 5.0,
                "dot_tick_rate": 1.0
            }
        }
        
        # Material penetration properties
        self.materials = {
            "flesh": {"resistance": 0.0, "damage_multiplier": 1.0},
            "armor": {"resistance": 0.8, "damage_multiplier": 0.5},
            "shield": {"resistance": 0.6, "damage_multiplier": 0.7},
            "wood": {"resistance": 0.3, "damage_multiplier": 0.9},
            "metal": {"resistance": 0.7, "damage_multiplier": 0.6},
            "concrete": {"resistance": 0.9, "damage_multiplier": 0.4},
            "glass": {"resistance": 0.1, "damage_multiplier": 1.2}
        }
        
        # Hitbox multipliers
        self.hitbox_multipliers = {
            "head": 2.0,
            "neck": 1.8,
            "torso": 1.0,
            "upper_arm": 0.8,
            "lower_arm": 0.6,
            "hand": 0.5,
            "upper_leg": 0.7,
            "lower_leg": 0.5,
            "foot": 0.4
        }
        
        # Status effect tracking
        self.active_effects = {}  # {entity_id: {effect_type: {start_time, duration, strength, etc}}}
        
        # Register events
        self.event_manager.register("weapon_fired", self.on_weapon_fired)
        self.event_manager.register("explosion", self.on_explosion)
        self.event_manager.register("tick", self.update)
        self.event_manager.register("player_respawn", self.on_player_respawn)
        
        # Damage history for kill feed and analytics
        self.damage_history = {}  # {entity_id: [{source, timestamp, damage, type, etc}]}
        
        # Configuration
        self.config = {
            "friendly_fire": False,
            "team_damage_multiplier": 0.3,
            "critical_hit_chance": 0.05,
            "critical_hit_multiplier": 1.5,
            "damage_falloff_start": 20.0,  # Distance in meters
            "damage_falloff_end": 100.0,
            "minimum_damage_percent": 0.4,
            "penetration_enabled": True,
            "max_penetrations": 3,
            "penetration_damage_decay": 0.6,  # Damage multiplier per penetration
            "show_damage_numbers": True,
            "headshot_always_critical": True,
            "environmental_damage_enabled": True,
            "damage_history_duration": 10.0,  # How long to keep damage history in seconds
            "kill_credit_timeout": 5.0      # Time window for kill credit in seconds
        }
    
    def update(self, event_data):
        """
        Update method called every tick to process ongoing effects.
        
        Args:
            event_data: Data associated with the tick event
        """
        delta_time = event_data.get("delta_time", 0.0)
        current_time = self.time_manager.get_current_time()
        
        # Process damage over time effects
        entities_to_update = list(self.active_effects.keys())
        for entity_id in entities_to_update:
            # Check if entity still exists
            entity = self._get_entity_by_id(entity_id)
            if not entity:
                # Entity no longer exists, clean up effects
                self.active_effects.pop(entity_id, None)
                continue
                
            effects = self.active_effects[entity_id]
            effects_to_remove = []
            
            for effect_type, effect_data in effects.items():
                # Check if effect has expired
                if current_time > effect_data["start_time"] + effect_data["duration"]:
                    effects_to_remove.append(effect_type)
                    continue
                
                # Process DoT ticks
                if "last_tick_time" in effect_data and "tick_rate" in effect_data:
                    time_since_last_tick = current_time - effect_data["last_tick_time"]
                    if time_since_last_tick >= effect_data["tick_rate"]:
                        # Apply damage tick
                        self._apply_dot_tick(entity, effect_data)
                        effect_data["last_tick_time"] = current_time
            
            # Remove expired effects
            for effect_type in effects_to_remove:
                self._remove_status_effect(entity_id, effect_type)
        
        # Clean up old damage history entries
        self._clean_damage_history(current_time)
    
    def apply_damage(self, target, damage_info):
        """
        Apply damage to a target entity with all relevant modifiers.
        
        Args:
            target: Entity receiving damage
            damage_info: Dictionary containing damage information:
                - amount: Base damage amount
                - type: Damage type (physical, explosive, etc.)
                - source: Entity causing the damage
                - weapon_id: ID of weapon used (if applicable)
                - hit_location: Body part hit (if applicable)
                - direction: Direction of damage for knockback
                - position: World position of hit
                - critical: Whether hit is critical (can be auto-determined)
                - penetration_count: Number of objects already penetrated
        
        Returns:
            Dictionary with applied damage information
        """
        if not target or not hasattr(target, "health") or target.health <= 0:
            return {"applied": 0, "killed": False}
        
        # Extract info from damage_info with defaults
        base_damage = damage_info.get("amount", 0)
        damage_type = damage_info.get("type", "physical")
        source = damage_info.get("source", None)
        weapon_id = damage_info.get("weapon_id", None)
        hit_location = damage_info.get("hit_location", "torso")
        direction = damage_info.get("direction", (0, 0, -1))
        position = damage_info.get("position", target.get_position())
        is_critical = damage_info.get("critical", False)
        penetration_count = damage_info.get("penetration_count", 0)
        
        # Check friendly fire
        if not self._allow_friendly_fire(source, target):
            if not self.config["friendly_fire"]:
                return {"applied": 0, "killed": False}
            # Apply team damage modifier
            base_damage *= self.config["team_damage_multiplier"]
        
        # Apply hitbox multiplier
        if hit_location in self.hitbox_multipliers:
            base_damage *= self.hitbox_multipliers[hit_location]
            
            # Auto-critical for headshots if enabled
            if hit_location == "head" and self.config["headshot_always_critical"]:
                is_critical = True
        
        # Calculate critical hit if not already determined
        if not is_critical and random.random() < self.config["critical_hit_chance"]:
            is_critical = True
        
        # Apply critical hit multiplier
        if is_critical:
            base_damage *= self.config["critical_hit_multiplier"]
        
        # Apply damage type modifiers
        if damage_type in self.damage_types:
            type_data = self.damage_types[damage_type]
            
            # Apply penetration modifier
            if penetration_count > 0:
                penetration_factor = type_data.get("penetration_factor", 1.0)
                decay_multiplier = self.config["penetration_damage_decay"] ** penetration_count
                base_damage *= penetration_factor * decay_multiplier
        
        # Apply distance falloff
        if "distance" in damage_info and weapon_id:
            distance = damage_info["distance"]
            base_damage = self._apply_distance_falloff(base_damage, distance, weapon_id)
        
        # Apply target-specific modifiers (armor, resistances, etc.)
        damage_multiplier = 1.0
        
        # Check for shield
        if hasattr(target, "shield") and target.shield > 0:
            if damage_type in self.damage_types:
                # Apply shield-specific multiplier if exists
                shield_multiplier = self.damage_types[damage_type].get("shield_multiplier", 1.0)
                damage_multiplier *= shield_multiplier
            
            material = "shield"
        # Check for armor
        elif hasattr(target, "armor") and target.armor > 0:
            material = "armor"
        else:
            material = "flesh"
            
        # Apply material-based modifiers
        if material in self.materials:
            material_data = self.materials[material]
            
            # Calculate penetration effects
            if damage_type in self.damage_types:
                type_pen_factor = self.damage_types[damage_type].get("penetration_factor", 1.0)
                material_resistance = material_data.get("resistance", 0.0)
                
                # Effective resistance after penetration factor
                effective_resistance = material_resistance / type_pen_factor
                damage_multiplier *= 1.0 - min(0.9, effective_resistance)  # Cap at 90% reduction
            
            # Apply material damage multiplier
            damage_multiplier *= material_data.get("damage_multiplier", 1.0)
        
        # Calculate final damage
        final_damage = max(1, round(base_damage * damage_multiplier))
        
        # Apply damage to target (shield first, then armor, then health)
        damage_remaining = final_damage
        shield_damage = 0
        armor_damage = 0
        health_damage = 0
        
        # Apply to shield
        if hasattr(target, "shield") and target.shield > 0:
            shield_damage = min(target.shield, damage_remaining)
            target.shield -= shield_damage
            damage_remaining -= shield_damage
        
        # Apply to armor
        if damage_remaining > 0 and hasattr(target, "armor") and target.armor > 0:
            armor_damage = min(target.armor, damage_remaining)
            target.armor -= armor_damage
            damage_remaining -= armor_damage
        
        # Apply to health
        if damage_remaining > 0:
            health_damage = damage_remaining
            target.health -= health_damage
        
        # Check if target was killed
        killed = target.health <= 0
        if killed:
            self._handle_kill(target, source, damage_info)
        
        # Apply knockback effect
        if hasattr(target, "apply_knockback"):
            knockback_strength = final_damage * 0.05  # Scale knockback with damage
            target.apply_knockback(direction, knockback_strength)
        
        # Apply status effects based on damage type
        self._apply_status_effects(target, damage_type, final_damage)
        
        # Create damage numbers if enabled
        if self.config["show_damage_numbers"]:
            self._spawn_damage_number(target, final_damage, position, is_critical, damage_type)
        
        # Record damage in history
        self._record_damage(target.id, {
            "source": source.id if source else None,
            "weapon_id": weapon_id,
            "damage": final_damage,
            "shield_damage": shield_damage,
            "armor_damage": armor_damage,
            "health_damage": health_damage,
            "type": damage_type,
            "hit_location": hit_location,
            "critical": is_critical,
            "timestamp": self.time_manager.get_current_time(),
            "killed": killed
        })
        
        # Dispatch damage event
        self.event_manager.dispatch("damage_applied", {
            "target": target,
            "source": source,
            "damage": final_damage,
            "type": damage_type,
            "hit_location": hit_location,
            "critical": is_critical,
            "killed": killed
        })
        
        # Send analytics
        self._track_damage_analytics(target, source, final_damage, damage_type, killed)
        
        # Return damage application results
        return {
            "applied": final_damage,
            "shield_damage": shield_damage,
            "armor_damage": armor_damage,
            "health_damage": health_damage,
            "critical": is_critical,
            "killed": killed
        }
    
    def apply_explosion_damage(self, position, explosion_info):
        """
        Apply explosion damage to all entities within radius.
        
        Args:
            position: Center position of explosion
            explosion_info: Dictionary containing explosion information:
                - radius: Explosion radius
                - damage: Maximum damage at center
                - falloff: Damage falloff type ("linear", "quadratic", etc.)
                - type: Damage type (default: "explosive")
                - source: Entity causing the explosion
                - weapon_id: ID of weapon used (if applicable)
                
        Returns:
            List of entities damaged with their damage info
        """
        radius = explosion_info.get("radius", 5.0)
        max_damage = explosion_info.get("damage", 100)
        falloff_type = explosion_info.get("falloff", "quadratic")
        damage_type = explosion_info.get("type", "explosive")
        source = explosion_info.get("source", None)
        weapon_id = explosion_info.get("weapon_id", None)
        
        # Find all entities within radius
        entities = self._get_entities_in_radius(position, radius)
        results = []
        
        for entity, distance in entities:
            # Skip the source entity if it's in the list
            if source and entity.id == source.id:
                continue
                
            # Calculate damage based on distance and falloff
            damage_percent = self._calculate_explosion_falloff(distance, radius, falloff_type)
            damage = max_damage * damage_percent
            
            if damage <= 0:
                continue
                
            # Check line of sight for partial cover protection
            obstruction_modifier = self._check_explosion_obstruction(position, entity.get_position())
            damage *= obstruction_modifier
            
            if damage <= 0:
                continue
                
            # Calculate direction for knockback
            direction = self._normalize(self._vector_subtract(entity.get_position(), position))
            
            # Apply damage
            damage_info = {
                "amount": damage,
                "type": damage_type,
                "source": source,
                "weapon_id": weapon_id,
                "direction": direction,
                "position": position,
                "distance": distance
            }
            
            result = self.apply_damage(entity, damage_info)
            
            if result["applied"] > 0:
                results.append({
                    "entity": entity,
                    "damage": result["applied"],
                    "killed": result["killed"]
                })
                
        return results
    
    def on_weapon_fired(self, event_data):
        """
        Handle weapon fired events for hit detection and damage application.
        
        Args:
            event_data: Data associated with the weapon fired event:
                - shooter: Entity that fired the weapon
                - weapon_id: ID of the weapon used
                - origin: Origin position of the shot
                - direction: Direction vector of the shot
                - spread: Accuracy/spread factor
        """
        shooter = event_data.get("shooter")
        weapon_id = event_data.get("weapon_id")
        origin = event_data.get("origin")
        direction = event_data.get("direction")
        spread = event_data.get("spread", 0.0)
        
        if not shooter or not weapon_id or not origin or not direction:
            return
            
        # Get weapon configuration
        weapon_config = get_weapon_config(weapon_id)
        if not weapon_config:
            return
            
        # Extract weapon damage properties
        base_damage = weapon_config.get("damage", 20)
        damage_type = weapon_config.get("damage_type", "physical")
        penetration_power = weapon_config.get("penetration", 1.0)
        penetration_enabled = weapon_config.get("can_penetrate", True) and self.config["penetration_enabled"]
        max_range = weapon_config.get("max_range", 1000.0)
        
        # Apply spread to direction if needed
        if spread > 0:
            direction = self._apply_weapon_spread(direction, spread)
        
        # Perform raycast for hit detection
        hit_entities = []
        
        if penetration_enabled:
            # Multi-hit raycast for penetration
            hits = self._penetration_raycast(origin, direction, max_range, penetration_power, 
                                            self.config["max_penetrations"])
            hit_entities = hits
        else:
            # Single hit raycast
            hit_info = raycast(origin, direction, max_range)
            if hit_info["hit"]:
                hit_entities = [hit_info]
        
        # Process hits and apply damage
        results = []
        penetration_count = 0
        
        for hit in hit_entities:
            if not hit["hit"]:
                continue
                
            entity = hit.get("entity")
            if not entity:
                continue
                
            # Calculate hit details
            hit_position = hit.get("position")
            hit_normal = hit.get("normal", (0, 0, 1))
            hit_material = hit.get("material", "flesh")
            distance = hit.get("distance", 0)
            hit_location = hit.get("hitbox_region", "torso")
            
            # Check if this is a valid target for damage
            if not self._is_damageable_entity(entity):
                # If not damageable but penetrable, count as penetration
                if hit_material in self.materials and penetration_enabled:
                    penetration_count += 1
                continue
            
            # Calculate damage direction (for knockback)
            damage_direction = direction
            
            # Create damage info
            damage_info = {
                "amount": base_damage,
                "type": damage_type,
                "source": shooter,
                "weapon_id": weapon_id,
                "hit_location": hit_location,
                "direction": damage_direction,
                "position": hit_position,
                "distance": distance,
                "penetration_count": penetration_count
            }
            
            # Apply damage
            result = self.apply_damage(entity, damage_info)
            
            # Track result
            results.append({
                "entity": entity,
                "hit_location": hit_location,
                "damage": result["applied"],
                "killed": result["killed"],
                "critical": result.get("critical", False)
            })
            
            # Count this hit for penetration
            penetration_count += 1
            
        # Create hit markers if any damage was applied
        if results and shooter and hasattr(shooter, "id") and isinstance(shooter, Player):
            self._create_hit_markers(shooter.id, results)
            
        return results
    
    def on_explosion(self, event_data):
        """
        Handle explosion events.
        
        Args:
            event_data: Data associated with the explosion event
        """
        position = event_data.get("position")
        if not position:
            return
            
        # Apply explosion damage
        explosion_info = {
            "radius": event_data.get("radius", 5.0),
            "damage": event_data.get("damage", 100),
            "falloff": event_data.get("falloff", "quadratic"),
            "type": event_data.get("type", "explosive"),
            "source": event_data.get("source"),
            "weapon_id": event_data.get("weapon_id")
        }
        
        results = self.apply_explosion_damage(position, explosion_info)
        
        # Create hit markers for player source
        source = event_data.get("source")
        if results and source and hasattr(source, "id") and isinstance(source, Player):
            self._create_hit_markers(source.id, results)
            
        return results
    
    def on_player_respawn(self, event_data):
        """
        Handle player respawn events to clear any active effects.
        
        Args:
            event_data: Data associated with the player respawn event
        """
        player_id = event_data.get("player_id")
        if player_id:
            # Remove all status effects for respawned player
            self.active_effects.pop(player_id, None)
    
    def _apply_weapon_spread(self, direction, spread):
        """
        Apply random spread to a weapon shot direction.
        
        Args:
            direction: Original normalized direction vector
            spread: Spread amount (0.0 to 1.0)
            
        Returns:
            New direction vector with spread applied
        """
        # Limit maximum spread
        spread = min(1.0, max(0.0, spread))
        
        # Calculate random deviation angles
        max_angle = spread * 0.05  # 5 degrees at max spread
        angle_h = random.uniform(-max_angle, max_angle)
        angle_v = random.uniform(-max_angle, max_angle)
        
        # Convert angles to radians
        angle_h_rad = math.radians(angle_h)
        angle_v_rad = math.radians(angle_v)
        
        # Apply rotation to direction vector
        x, y, z = direction
        
        # Horizontal rotation
        x_new = x * math.cos(angle_h_rad) - z * math.sin(angle_h_rad)
        z_new = x * math.sin(angle_h_rad) + z * math.cos(angle_h_rad)
        
        # Vertical rotation
        y_new = y * math.cos(angle_v_rad) - z_new * math.sin(angle_v_rad)
        z_new = y * math.sin(angle_v_rad) + z_new * math.cos(angle_v_rad)
        
        # Normalize the new direction
        return self._normalize((x_new, y_new, z_new))
    
    def _penetration_raycast(self, origin, direction, max_range, penetration_power, max_penetrations):
        """
        Perform a raycast that can penetrate multiple objects.
        
        Args:
            origin: Origin position of the ray
            direction: Direction vector of the ray
            max_range: Maximum distance the ray can travel
            penetration_power: Base penetration power of the projectile
            max_penetrations: Maximum number of objects that can be penetrated
            
        Returns:
            List of hit results for each penetrated object
        """
        hits = []
        current_origin = origin
        remaining_range = max_range
        remaining_power = penetration_power
        penetration_count = 0
        
        while remaining_power > 0 and penetration_count < max_penetrations and remaining_range > 0:
            # Cast ray from current position
            hit_info = raycast(current_origin, direction, remaining_range)
            
            if not hit_info["hit"]:
                break
                
            # Add hit to results
            hits.append(hit_info)
            
            # Update remaining range
            distance = hit_info.get("distance", 0)
            remaining_range -= distance
            
            # Check if we should penetrate this object
            entity = hit_info.get("entity")
            material = hit_info.get("material", "flesh")
            
            # Get material resistance
            material_resistance = 0.5  # Default
            if material in self.materials:
                material_resistance = self.materials[material].get("resistance", 0.5)
            
            # Calculate power reduction
            power_reduction = 1.0 + material_resistance * 2.0
            remaining_power -= power_reduction
            
            # If no power left, stop penetration
            if remaining_power <= 0:
                break
                
            # Update penetration count
            penetration_count += 1
            
            # Move origin slightly past the hit point to avoid self-intersection
            hit_position = hit_info.get("position", current_origin)
            penetration_offset = 0.05  # Small offset to avoid hitting the same surface
            current_origin = (
                hit_position[0] + direction[0] * penetration_offset,
                hit_position[1] + direction[1] * penetration_offset,
                hit_position[2] + direction[2] * penetration_offset
            )
        
        return hits
    
    def _apply_distance_falloff(self, damage, distance, weapon_id):
        """
        Apply distance-based damage falloff.
        
        Args:
            damage: Base damage amount
            distance: Distance to target
            weapon_id: ID of weapon used
            
        Returns:
            Modified damage after falloff
        """
        # Get weapon-specific falloff if available
        weapon_config = get_weapon_config(weapon_id)
        if weapon_config:
            falloff_start = weapon_config.get("falloff_start", self.config["damage_falloff_start"])
            falloff_end = weapon_config.get("falloff_end", self.config["damage_falloff_end"])
            min_damage_percent = weapon_config.get("min_damage_percent", self.config["minimum_damage_percent"])
        else:
            falloff_start = self.config["damage_falloff_start"]
            falloff_end = self.config["damage_falloff_end"]
            min_damage_percent = self.config["minimum_damage_percent"]
        
        # No falloff if distance is within start range
        if distance <= falloff_start:
            return damage
            
        # Maximum falloff if distance is beyond end range
        if distance >= falloff_end:
            return damage * min_damage_percent
            
        # Linear interpolation for distances in between
        falloff_range = falloff_end - falloff_start
        falloff_percent = (distance - falloff_start) / falloff_range
        damage_percent = 1.0 - ((1.0 - min_damage_percent) * falloff_percent)
        
        return damage * damage_percent
    
    def _apply_status_effects(self, target, damage_type, damage_amount):
        """
        Apply status effects based on damage type.
        
        Args:
            target: Entity to apply effects to
            damage_type: Type of damage
            damage_amount: Amount of damage dealt
        """
        if not target or not hasattr(target, "id"):
            return
            
        # Get entity ID for effect tracking
        entity_id = target.id
        
        # Initialize effects for entity if not exists
        if entity_id not in self.active_effects:
            self.active_effects[entity_id] = {}
            
        current_time = self.time_manager.get_current_time()
        
        # Apply appropriate effects based on damage type
        if damage_type == "fire":
            # Fire applies burning DoT
            effect_data = {
                "type": "burning",
                "start_time": current_time,
                "duration": self.damage_types["fire"].get("dot_duration", 3.0),
                "strength": damage_amount * 0.2,  # 20% of initial damage per tick
                "tick_rate": self.damage_types["fire"].get("dot_tick_rate", 0.5),
                "last_tick_time": current_time,
                "source_type": damage_type
            }
            
            # Add or refresh effect
            self.active_effects[entity_id]["burning"] = effect_data
            
            # Visual effect
            self._apply_visual_effect(target, "burning", effect_data["duration"])
            
        elif damage_type == "cryo":
            # Cryo applies slowing effect
            slow_factor = self.damage_types["cryo"].get("slow_factor", 0.3)
            effect_data = {
                "type": "slowed",
                "start_time": current_time,
                "duration": self.damage_types["cryo"].get("slow_duration", 2.0),
                "strength": slow_factor,
                "source_type": damage_type
            }
            
            # Add or refresh effect
            self.active_effects[entity_id]["slowed"] = effect_data
            
            # Apply movement speed modifier to entity
            if hasattr(target, "add_movement_modifier"):
                target.add_movement_modifier("cryo_slow", 1.0 - slow_factor, effect_data["duration"])
                
            # Visual effect
            self._apply_visual_effect(target, "frozen", effect_data["duration"])
            
        elif damage_type == "poison":
            # Poison applies DoT
            effect_data = {
                "type": "poisoned",
                "start_time": current_time,
                "duration": self.damage_types["poison"].get("dot_duration", 5.0),
                "strength": damage_amount * 0.15,  # 15% of initial damage per tick
                "tick_rate": self.damage_types["poison"].get("dot_tick_rate", 1.0),
                "last_tick_time": current_time,
                "source_type": damage_type
            }
            
            # Add or refresh effect
            self.active_effects[entity_id]["poisoned"] = effect_data
            
            # Visual effect
            self._apply_visual_effect(target, "poisoned", effect_data["duration"])
    
    def _apply_visual_effect(self, entity, effect_type, duration):
        """
        Apply visual effect to an entity.
        
        Args:
            entity: Target entity
            effect_type: Type of visual effect
            duration: Duration of effect in seconds
        """
        if not entity or not hasattr(entity, "add_visual_effect"):
            return
            
        # Get effect color from damage type if available
        color = (255, 255, 255)  # Default white
        
        if effect_type == "burning" and "fire" in self.damage_types:
            color = self.damage_types["fire"].get("color", (255, 70, 0))
        elif effect_type == "frozen" and "cryo" in self.damage_types:
            color = self.damage_types["cryo"].get("color", (150, 220, 255))
        elif effect_type == "poisoned" and "poison" in self.damage_types:
            color = self.damage_types["poison"].get("color", (100, 200, 50))
            
        # Add visual effect to entity
        entity.add_visual_effect(effect_type, duration, color)
        
        # Play effect sound
        self._play_effect_sound(entity, effect_type)
    
    def _apply_dot_tick(self, entity, effect_data):
        """
        Apply a damage over time tick to an entity.
        
        Args:
            entity: Target entity
            effect_data: Data for the DoT effect
        """
        if not entity or entity.health <= 0:
            return
            
        # Extract effect info
        damage = effect_data.get("strength", 0)
        effect_type = effect_data.get("type", "burning")
        source_type = effect_data.get("source_type", "fire")
        
        # Create basic damage info for the tick
        damage_info = {
            "amount": damage,
            "type": source_type,
            "source": effect_data.get("source", None),
            "hit_location": "torso",  # Default for DoT
            "critical": False,  # DoT ticks are never critical
            "is_dot_tick": True
        }
        
        # Apply the tick damage
        self.apply_damage(entity, damage_info)
    
    def _remove_status_effect(self, entity_id, effect_type):
        """
        Remove a status effect from an entity.
        
        Args:
            entity_id: ID of the entity
            effect_type: Type of effect to remove
        """
        if entity_id not in self.active_effects:
            return
            
        # Remove the effect
        if effect_type in self.active_effects[entity_id]:
            effect_data = self.active_effects[entity_id].pop(effect_type)
            
            # Get entity
            entity = self._get_entity_by_id(entity_id)
            if not entity:
                return
                
            # Remove movement modifiers if applicable
            if effect_type == "slowed" and hasattr(entity, "remove_movement_modifier"):
                entity.remove_movement_modifier("cryo_slow")
                
            # Remove visual effects if applicable
            if hasattr(entity, "remove_visual_effect"):
                # Map effect types to visual effect types
                if effect_type == "burning":
                    entity.remove_visual_effect("burning")
                elif effect_type == "slowed":
                    entity.remove_visual_effect("frozen")
                elif effect_type == "poisoned":
                    entity.remove_visual_effect("poisoned")
    
    def _get_entity_by_id(self, entity_id):
        """
        Get entity instance by ID.
        
        Args:
            entity_id: ID of the entity to find
            
        Returns:
            Entity instance or None if not found
        """
        # This would typically use a scene or entity manager
        # For example: return entity_manager.get_entity(entity_id)
        # Implementation depends on how entities are stored in the game
        
        # Placeholder implementation
        from game.entityManager import get_entity
        return get_entity(entity_id)
    
    def _get_entities_in_radius(self, position, radius):
        """
        Get all entities within a radius of a position.
        
        Args:
            position: Center position
            radius: Radius to check
            
        Returns:
            List of (entity, distance) tuples for entities in range
        """
        # This would typically use spatial partitioning or physics
        # For example: return physics_world.query_sphere(position, radius)
        
        # Placeholder implementation
        from game.entityManager import get_entities_in_radius
        entities = get_entities_in_radius(position, radius)
        
        # Calculate distances
        result = []
        for entity in entities:
            if hasattr(entity, "get_position"):
                entity_pos = entity.get_position()
                distance = self._calculate_distance(position, entity_pos)
                result.append((entity, distance))
                
        return result
    
    def _calculate_distance(self, pos1, pos2):
        """Calculate distance between two 3D positions."""
        return math.sqrt((pos2[0] - pos1[0])**2 + 
                         (pos2[1] - pos1[1])**2 + 
                         (pos2[2] - pos1[2])**2)
    
    def _normalize(self, vector):
        """Normalize a 3D vector."""
        length = math.sqrt(vector[0]**2 + vector[1]**2 + vector[2]**2)
        if length == 0:
            return (0, 0, 1)  # Default forward direction
        return (vector[0]/length, vector[1]/length, vector[2]/length)
    
    def _vector_subtract(self, v1, v2):
        """Subtract vector v2 from v1."""
        return (v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2])
    
    def _calculate_explosion_falloff(self, distance, radius, falloff_type):
        """
        Calculate explosion damage falloff based on distance.
        
        Args:
            distance: Distance from explosion center
            radius: Explosion radius
            falloff_type: Type of falloff calculation
            
        Returns:
            Damage percentage (0.0 to 1.0)
        """
        # Ensure distance is in valid range
        if distance >= radius:
            return 0.0
            
        if distance <= 0:
            return 1.0
            
        # Calculate normalized distance
        normalized_dist = distance / radius
        
        # Apply falloff formula based on type
        if falloff_type == "linear":
            return 1.0 - normalized_dist
        elif falloff_type == "quadratic":
            return 1.0 - (normalized_dist * normalized_dist)
        elif falloff_type == "exponential":
            return math.exp(-3.0 * normalized_dist)
        else:  # Default to linear
            return 1.0 - normalized_dist
    
    def _check_explosion_obstruction(self, explosion_pos, entity_pos):
        """
        Check for obstructions between explosion and entity.
        
        Args:
            explosion_pos: Explosion center position
            entity_pos: Entity position
            
        Returns:
            Damage modifier based on obstruction (0.0 to 1.0)
        """
        # Cast ray from explosion to entity
        direction = self._normalize(self._vector_subtract(entity_pos, explosion_pos))
        distance = self._calculate_distance(explosion_pos, entity_pos)
        
        hit_info = raycast(explosion_pos, direction, distance * 0.99)  # Slightly shorter to avoid self-hits
        
        # If nothing hit, full damage
        if not hit_info["hit"]:
            return 1.0
            
        # If hit something other than target entity, reduce damage
        hit_entity = hit_info.get("entity")
        if hit_entity:
            return 0.5  # Partial cover
        else:
            return 0.25  # Solid cover
    
    def _create_hit_markers(self, player_id, hit_results):
        """
        Create hit markers for player feedback.
        
        Args:
            player_id: ID of player who made the hits
            hit_results: List of hit result data
        """
        # Find player by ID
        player = self._get_entity_by_id(player_id)
        if not player or not isinstance(player, Player):
            return
            
        # Check if player has hit marker system
        if not hasattr(player, "show_hit_marker"):
            return
            
        # Process each hit
        for hit in hit_results:
            # Extract hit info
            entity = hit.get("entity")
            damage = hit.get("damage", 0)
            killed = hit.get("killed", False)
            critical = hit.get("critical", False)
            
            # Determine hit marker type
            if killed:
                marker_type = "kill"
            elif critical:
                marker_type = "critical"
            else:
                marker_type = "hit"
                
            # Show hit marker to player
            player.show_hit_marker(marker_type, damage)
            
            # Play hit sound
            if entity:
                entity_type = "human" if isinstance(entity, Player) else "monster"
                self._play_hit_sound(player, entity_type, critical, killed)
    
    def _play_hit_sound(self, player, target_type, critical, killed):
        """
        Play appropriate hit sound for player feedback.
        
        Args:
            player: Player entity
            target_type: Type of target hit
            critical: Whether hit was critical
            killed: Whether hit killed the target
        """
        # Determine sound to play
        sound_name = "hit"
        
        if killed:
            sound_name = "kill"
        elif critical:
            sound_name = "critical_hit"
            
        # Modify sound based on target type
        sound_name += "_" + target_type
        
        # Play sound for player
        if hasattr(player, "play_sound"):
            player.play_sound(sound_name)
    
    def _play_effect_sound(self, entity, effect_type):
        """
        Play sound for status effect application.
        
        Args:
            entity: Target entity
            effect_type: Type of effect applied
        """
        # Map effect types to sound names
        sound_mapping = {
            "burning": "effect_burning",
            "frozen": "effect_freeze",
            "poisoned": "effect_poison"
        }
        
        # Get sound name
        sound_name = sound_mapping.get(effect_type, "effect_generic")
        
        # Play sound at entity position
        if hasattr(entity, "play_sound_at_position"):
            entity.play_sound_at_position(sound_name, entity.get_position())
    
    def _spawn_damage_number(self, entity, damage, position, is_critical, damage_type):
        """
        Spawn floating damage number for visual feedback.
        
        Args:
            entity: Entity that was damaged
            damage: Amount of damage dealt
            position: World position for the damage number
            is_critical: Whether damage was critical
            damage_type: Type of damage dealt
        """
        # Get color for damage type
        color = (255, 255, 255)  # Default white
        if damage_type in self.damage_types:
            color = self.damage_types[damage_type].get("color", (255, 255, 255))
            
        # Adjust size based on critical hit
        size = 1.0
        if is_critical:
            size = 1.5
            
        # Create floating text
        from fx.floatingText import create_floating_text
        text = str(int(damage))  # Round to integer
        
        # Add prefix/suffix for critical
        if is_critical:
            text = "!" + text + "!"
            
        create_floating_text(text, position, color, size)
    
    def _record_damage(self, entity_id, damage_data):
        """
        Record damage dealt to an entity in history.
        
        Args:
            entity_id: ID of damaged entity
            damage_data: Dictionary with damage details
        """
        # Initialize history for entity
        if entity_id not in self.damage_history:
            self.damage_history[entity_id] = []
            
        # Add damage to history
        self.damage_history[entity_id].append(damage_data)
        
        # Trim history if too long
        max_history = 20  # Keep last 20 damage events per entity
        if len(self.damage_history[entity_id]) > max_history:
            self.damage_history[entity_id] = self.damage_history[entity_id][-max_history:]
    
    def _clean_damage_history(self, current_time):
        """
        Clean up old damage history entries.
        
        Args:
            current_time: Current game time
        """
        # Maximum age for damage records
        max_age = self.config["damage_history_duration"]
        
        # Check all entities
        entities_to_update = list(self.damage_history.keys())
        for entity_id in entities_to_update:
            # Filter out old entries
            self.damage_history[entity_id] = [
                entry for entry in self.damage_history[entity_id]
                if current_time - entry.get("timestamp", 0) <= max_age
            ]
            
            # Remove empty lists
            if not self.damage_history[entity_id]:
                del self.damage_history[entity_id]
    
    def _handle_kill(self, target, source, damage_info):
        """
        Handle entity kill event.
        
        Args:
            target: Entity that was killed
            source: Entity that caused the kill
            damage_info: Dictionary with damage details
        """
        # Ignore if source is invalid
        if not source or not hasattr(source, "id"):
            return
            
        # Check if target is a valid killable entity
        if not self._is_valid_kill_target(target):
            return
            
        # Get kill type based on damage info
        kill_type = damage_info.get("type", "physical")
        weapon_id = damage_info.get("weapon_id", None)
        hit_location = damage_info.get("hit_location", "torso")
        
        # Determine if it's a headshot
        is_headshot = hit_location == "head"
        
        # Create kill event data
        kill_data = {
            "killer_id": source.id,
            "victim_id": target.id,
            "weapon_id": weapon_id,
            "damage_type": kill_type,
            "headshot": is_headshot,
            "timestamp": self.time_manager.get_current_time()
        }
        
        # Dispatch kill event
        self.event_manager.dispatch("entity_killed", kill_data)
        
        # Update kill feed
        self._update_kill_feed(source, target, weapon_id, is_headshot)
        
        # Award kill to source if it's a player
        if isinstance(source, Player):
            self._award_kill(source, target, kill_data)
            
        # Handle victim death
        self._handle_victim_death(target, source, kill_data)
    
    def _is_valid_kill_target(self, entity):
        """
        Check if entity is a valid kill target.
        
        Args:
            entity: Entity to check
            
        Returns:
            True if entity is a valid kill target
        """
        return (isinstance(entity, Player) or 
                isinstance(entity, Enemy) or 
                (hasattr(entity, "is_killable") and entity.is_killable))
    
    def _update_kill_feed(self, killer, victim, weapon_id, headshot):
        """
        Update the kill feed UI.
        
        Args:
            killer: Entity that made the kill
            victim: Entity that was killed
            weapon_id: ID of weapon used
            headshot: Whether kill was a headshot
        """
        # Get names for killer and victim
        killer_name = killer.name if hasattr(killer, "name") else "Unknown"
        victim_name = victim.name if hasattr(victim, "name") else "Unknown"
        
        # Get weapon name
        weapon_name = "Unknown"
        weapon_config = get_weapon_config(weapon_id)
        if weapon_config:
            weapon_name = weapon_config.get("name", "Unknown Weapon")
            
        # Create kill feed entry
        kill_feed_entry = {
            "killer": killer_name,
            "victim": victim_name,
            "weapon": weapon_name,
            "headshot": headshot,
            "timestamp": self.time_manager.get_current_time()
        }
        
        # Add to kill feed
        from ui.killFeed import add_kill_feed_entry
        add_kill_feed_entry(kill_feed_entry)
    
    def _award_kill(self, player, victim, kill_data):
        """
        Award kill to player, including points and stats.
        
        Args:
            player: Player who made the kill
            victim: Entity that was killed
            kill_data: Dictionary with kill details
        """
        # Base points for a kill
        points = 100
        
        # Bonus points for headshot
        if kill_data.get("headshot", False):
            points += 50
            
        # Bonus points for killing special targets
        if hasattr(victim, "point_value"):
            points += victim.point_value
            
        # Award points to player
        if hasattr(player, "add_points"):
            player.add_points(points)
            
        # Update player stats
        if hasattr(player, "stats"):
            player.stats.add_kill()
            
            # Track weapon-specific kill
            weapon_id = kill_data.get("weapon_id")
            if weapon_id and hasattr(player.stats, "add_weapon_kill"):
                player.stats.add_weapon_kill(weapon_id)
                
            # Track headshot
            if kill_data.get("headshot", False) and hasattr(player.stats, "add_headshot"):
                player.stats.add_headshot()
    
    def _handle_victim_death(self, victim, killer, kill_data):
        """
        Handle victim death effects and events.
        
        Args:
            victim: Entity that was killed
            killer: Entity that caused the kill
            kill_data: Dictionary with kill details
        """
        # Handle player death
        if isinstance(victim, Player):
            # Update player stats
            if hasattr(victim, "stats"):
                victim.stats.add_death()
                
            # Trigger respawn process
            if hasattr(victim, "initiate_respawn"):
                victim.initiate_respawn()
        
        # Handle enemy death
        elif isinstance(victim, Enemy):
            # Drop loot if applicable
            if hasattr(victim, "drop_loot"):
                victim.drop_loot()
                
            # Spawn effects
            if hasattr(victim, "play_death_effects"):
                victim.play_death_effects()
                
            # Remove from active entities
            if hasattr(victim, "remove"):
                victim.remove()
    
    def _track_damage_analytics(self, target, source, damage, damage_type, killed):
        """
        Track damage for analytics system.
        
        Args:
            target: Entity that was damaged
            source: Entity that caused the damage
            damage: Amount of damage dealt
            damage_type: Type of damage
            killed: Whether target was killed
        """
        # Ensure analytics is available
        if not self.analytics:
            return
            
        # Basic damage tracking
        self.analytics.track_damage_dealt(damage, damage_type)
        
        # Track kills
        if killed:
            self.analytics.track_kill(source, target, damage_type)
            
        # Track weapon usage if applicable
        if hasattr(source, "current_weapon_id"):
            weapon_id = source.current_weapon_id
            self.analytics.track_weapon_damage(weapon_id, damage)
    
    def _allow_friendly_fire(self, source, target):
        """
        Check if friendly fire is allowed between entities.
        
        Args:
            source: Entity causing damage
            target: Entity receiving damage
            
        Returns:
            True if damage is allowed, False if friendly fire should be blocked
        """
        # If either entity is invalid, allow damage
        if not source or not target:
            return True
            
        # If friendly fire is enabled globally, allow damage
        if self.config["friendly_fire"]:
            return True
            
        # Check if entities have team information
        if not hasattr(source, "team") or not hasattr(target, "team"):
            return True
            
        # Check if they're on the same team
        return source.team != target.team
    
    def _is_damageable_entity(self, entity):
        """
        Check if entity can receive damage.
        
        Args:
            entity: Entity to check
            
        Returns:
            True if entity can be damaged
        """
        # Valid damageable entities must have health attribute
        if not entity or not hasattr(entity, "health"):
            return False
            
        # Check if entity is already dead
        if entity.health <= 0:
            return False
            
        # Check if entity is in invulnerable state
        if hasattr(entity, "is_invulnerable") and entity.is_invulnerable:
            return False
            
        return True
    
    def get_entity_last_damage_source(self, entity_id, time_window=None):
        """
        Get the last entity that damaged the specified entity.
        
        Args:
            entity_id: ID of the entity to check
            time_window: Optional time window in seconds (default: config kill_credit_timeout)
            
        Returns:
            ID of last damage source or None
        """
        if entity_id not in self.damage_history:
            return None
            
        # Get damage history for entity
        history = self.damage_history[entity_id]
        if not history:
            return None
            
        # Use configuration time window if not specified
        if time_window is None:
            time_window = self.config["kill_credit_timeout"]
            
        # Get current time
        current_time = self.time_manager.get_current_time()
        
        # Find the most recent damage within time window
        for entry in reversed(history):
            # Skip if too old
            if current_time - entry.get("timestamp", 0) > time_window:
                continue
                
            # Return source entity ID
            return entry.get("source")
            
        return None