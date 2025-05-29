"""
worldMap.py - MMORPG World Map Management System

This module handles the world map functionality for the MMORPG portion of the game,
including map loading, player positioning, zone transitions, world events,
points of interest, and fast travel systems.
"""

import json
import random
import os
from core.modules.eventManager import EventManager
from core.modules.resourceManager import ResourceManager
from core.modules.timeManager import TimeManager
from mmorpg.mechanics.questSystem import QuestSystem
from networking.engine.serverSync import ServerSync


class WorldMap:
    """Main class for managing the MMORPG world map."""
    
    def __init__(self, resource_manager=None, event_manager=None, time_manager=None):
        """Initialize the world map system."""
        self.resource_manager = resource_manager or ResourceManager()
        self.event_manager = event_manager or EventManager()
        self.time_manager = time_manager or TimeManager()
        self.server_sync = ServerSync()
        self.quest_system = QuestSystem()
        
        # World map data
        self.world_data = self._load_world_data()
        self.current_zone = None
        self.discovered_zones = set()
        self.points_of_interest = {}
        self.active_world_events = []
        self.weather_conditions = {}
        
        # Fast travel points
        self.fast_travel_points = {}
        self.unlocked_fast_travel = set()
        
        # Map visuals
        self.fog_of_war = {}
        self.map_markers = {}
        
        # Register for relevant events
        self.event_manager.register("player_zone_changed", self.on_zone_changed)
        self.event_manager.register("world_event_started", self.on_world_event_started)
        self.event_manager.register("world_event_completed", self.on_world_event_completed)
        self.event_manager.register("poi_discovered", self.on_poi_discovered)
        self.event_manager.register("time_cycle_changed", self.update_weather)
        
    def _load_world_data(self):
        """Load world map data from configuration files."""
        try:
            config_path = os.path.join("configs", "data", "mapData.json")
            with open(config_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading world map data: {e}")
            return self._get_default_world_data()
    
    def _get_default_world_data(self):
        """Return default world data if the config file can't be loaded."""
        return {
            "zones": {
                "starting_zone": {
                    "name": "Evergreen Valley",
                    "level_range": [1, 10],
                    "connections": ["forest_zone", "village_zone"],
                    "fast_travel_points": ["valley_shrine", "hunter_camp"]
                },
                "forest_zone": {
                    "name": "Misty Woods",
                    "level_range": [8, 15],
                    "connections": ["starting_zone", "mountain_zone"],
                    "fast_travel_points": ["ancient_tree", "river_crossing"]
                },
                "mountain_zone": {
                    "name": "Frostpeak Heights",
                    "level_range": [15, 25],
                    "connections": ["forest_zone", "desert_zone"],
                    "fast_travel_points": ["mountain_pass", "eagle_nest"]
                }
            },
            "world_events": {
                "bandit_raid": {
                    "zones": ["starting_zone", "forest_zone"],
                    "level_range": [5, 15],
                    "duration": 3600,  # seconds
                    "rewards": {"xp": 500, "gold": 100, "items": ["bandit_trophy"]}
                },
                "dragon_sighting": {
                    "zones": ["mountain_zone"],
                    "level_range": [20, 30],
                    "duration": 7200,  # seconds
                    "rewards": {"xp": 2000, "gold": 500, "items": ["dragon_scale"]}
                }
            }
        }
    
    def initialize_player_map(self, player_id, starting_zone="starting_zone"):
        """Initialize a new player's map data."""
        self.current_zone = starting_zone
        self.discovered_zones = {starting_zone}
        
        # Initialize fog of war for all zones (True means fogged)
        self.fog_of_war = {zone: True for zone in self.world_data["zones"]}
        self.fog_of_war[starting_zone] = False
        
        # Unlock default fast travel point
        initial_travel_point = self.world_data["zones"][starting_zone]["fast_travel_points"][0]
        self.unlocked_fast_travel.add(initial_travel_point)
        
        # Notify event system about new player
        self.event_manager.trigger("player_map_initialized", {
            "player_id": player_id,
            "zone": starting_zone
        })
        
        # Sync with server
        self._sync_player_map_data(player_id)
        
        return {
            "current_zone": self.current_zone,
            "discovered_zones": list(self.discovered_zones),
            "unlocked_fast_travel": list(self.unlocked_fast_travel)
        }
    
    def get_zone_info(self, zone_id):
        """Get detailed information about a specific zone."""
        if zone_id in self.world_data["zones"]:
            zone_data = self.world_data["zones"][zone_id].copy()
            
            # Add dynamic information
            zone_data["has_active_events"] = any(
                event["zone"] == zone_id for event in self.active_world_events
            )
            zone_data["weather"] = self.weather_conditions.get(zone_id, "clear")
            
            # Add points of interest for this zone
            zone_data["points_of_interest"] = [
                poi for poi_id, poi in self.points_of_interest.items() 
                if poi.get("zone") == zone_id
            ]
            
            return zone_data
        return None
    
    def discover_zone(self, zone_id):
        """Mark a zone as discovered by the player."""
        if zone_id in self.world_data["zones"] and zone_id not in self.discovered_zones:
            self.discovered_zones.add(zone_id)
            self.fog_of_war[zone_id] = False
            
            # Trigger discovery event
            self.event_manager.trigger("zone_discovered", {
                "zone_id": zone_id,
                "zone_name": self.world_data["zones"][zone_id]["name"]
            })
            
            # Check for related quests
            self.quest_system.update_zone_discovery(zone_id)
            
            # Check connected zones and make them visible but still fogged
            for connected_zone in self.world_data["zones"][zone_id].get("connections", []):
                if self.fog_of_war.get(connected_zone) is None:
                    self.fog_of_war[connected_zone] = True
            
            return True
        return False
    
    def change_zone(self, player_id, target_zone):
        """Handle player movement between zones."""
        current_zone = self.current_zone
        
        # Check if the target zone is connected to the current zone
        if target_zone not in self.world_data["zones"][current_zone].get("connections", []):
            return {"success": False, "error": "Zones are not connected for direct travel"}
        
        # Update current zone
        self.current_zone = target_zone
        
        # Discover the new zone if it hasn't been discovered yet
        if target_zone not in self.discovered_zones:
            self.discover_zone(target_zone)
        
        # Trigger zone change event
        self.event_manager.trigger("player_zone_changed", {
            "player_id": player_id,
            "previous_zone": current_zone,
            "new_zone": target_zone
        })
        
        # Sync with server
        self._sync_player_map_data(player_id)
        
        return {
            "success": True,
            "zone": target_zone,
            "zone_name": self.world_data["zones"][target_zone]["name"],
            "level_range": self.world_data["zones"][target_zone]["level_range"]
        }
    
    def fast_travel(self, player_id, destination_id):
        """Allow player to fast travel between unlocked points."""
        if destination_id not in self.unlocked_fast_travel:
            return {"success": False, "error": "Fast travel point not unlocked"}
        
        # Find which zone this fast travel point belongs to
        destination_zone = None
        for zone_id, zone_data in self.world_data["zones"].items():
            if destination_id in zone_data.get("fast_travel_points", []):
                destination_zone = zone_id
                break
        
        if not destination_zone:
            return {"success": False, "error": "Invalid fast travel destination"}
        
        # Update current zone
        previous_zone = self.current_zone
        self.current_zone = destination_zone
        
        # Trigger events
        self.event_manager.trigger("player_fast_traveled", {
            "player_id": player_id,
            "from_zone": previous_zone,
            "to_zone": destination_zone,
            "travel_point": destination_id
        })
        
        # Sync with server
        self._sync_player_map_data(player_id)
        
        return {
            "success": True,
            "zone": destination_zone,
            "zone_name": self.world_data["zones"][destination_zone]["name"],
            "travel_point": destination_id
        }
    
    def unlock_fast_travel_point(self, fast_travel_id):
        """Unlock a new fast travel point for the player."""
        # Check if the fast travel point exists in any zone
        exists = False
        for zone_data in self.world_data["zones"].values():
            if fast_travel_id in zone_data.get("fast_travel_points", []):
                exists = True
                break
        
        if not exists:
            return {"success": False, "error": "Fast travel point does not exist"}
        
        if fast_travel_id in self.unlocked_fast_travel:
            return {"success": False, "error": "Fast travel point already unlocked"}
        
        self.unlocked_fast_travel.add(fast_travel_id)
        self.event_manager.trigger("fast_travel_unlocked", {"point_id": fast_travel_id})
        
        return {"success": True, "point_id": fast_travel_id}
    
    def get_available_fast_travel_points(self):
        """Get a list of all fast travel points the player has unlocked."""
        result = []
        for point_id in self.unlocked_fast_travel:
            # Find which zone this point belongs to
            for zone_id, zone_data in self.world_data["zones"].items():
                if point_id in zone_data.get("fast_travel_points", []):
                    result.append({
                        "id": point_id,
                        "zone_id": zone_id,
                        "zone_name": zone_data["name"]
                    })
                    break
        
        return result
    
    def start_world_event(self, event_id, zone_id):
        """Start a world event in the specified zone."""
        if event_id not in self.world_data.get("world_events", {}):
            return {"success": False, "error": "Invalid world event"}
        
        event_data = self.world_data["world_events"][event_id].copy()
        
        # Check if this event can happen in this zone
        if zone_id not in event_data.get("zones", []):
            return {"success": False, "error": "Event not available in this zone"}
        
        # Add active event to the list
        active_event = {
            "id": event_id,
            "zone": zone_id,
            "start_time": self.time_manager.get_current_time(),
            "end_time": self.time_manager.get_current_time() + event_data["duration"],
            "participants": [],
            "progress": 0.0
        }
        
        self.active_world_events.append(active_event)
        
        # Trigger event start
        self.event_manager.trigger("world_event_started", {
            "event_id": event_id,
            "zone_id": zone_id,
            "duration": event_data["duration"]
        })
        
        return {
            "success": True,
            "event": active_event
        }
    
    def get_active_events_in_zone(self, zone_id):
        """Get all active world events in a specific zone."""
        return [
            event for event in self.active_world_events
            if event["zone"] == zone_id
        ]
    
    def join_world_event(self, player_id, event_id):
        """Add a player to an active world event."""
        for event in self.active_world_events:
            if event["id"] == event_id:
                if player_id not in event["participants"]:
                    event["participants"].append(player_id)
                
                self.event_manager.trigger("player_joined_world_event", {
                    "player_id": player_id,
                    "event_id": event_id
                })
                
                return {"success": True, "event": event}
        
        return {"success": False, "error": "Event not found or no longer active"}
    
    def add_map_marker(self, marker_id, marker_type, position, zone_id, description=""):
        """Add a marker to the player's map."""
        self.map_markers[marker_id] = {
            "type": marker_type,
            "position": position,
            "zone": zone_id,
            "description": description,
            "added_at": self.time_manager.get_current_time()
        }
        
        self.event_manager.trigger("map_marker_added", {
            "marker_id": marker_id,
            "type": marker_type,
            "zone": zone_id
        })
        
        return {"success": True, "marker_id": marker_id}
    
    def remove_map_marker(self, marker_id):
        """Remove a marker from the player's map."""
        if marker_id in self.map_markers:
            marker = self.map_markers.pop(marker_id)
            
            self.event_manager.trigger("map_marker_removed", {
                "marker_id": marker_id,
                "zone": marker["zone"]
            })
            
            return {"success": True}
        
        return {"success": False, "error": "Marker not found"}
    
    def get_map_markers_in_zone(self, zone_id):
        """Get all map markers in a specific zone."""
        return {
            marker_id: marker_data
            for marker_id, marker_data in self.map_markers.items()
            if marker_data["zone"] == zone_id
        }
    
    def register_point_of_interest(self, poi_id, zone_id, position, poi_type, name, description=""):
        """Register a new point of interest on the map."""
        self.points_of_interest[poi_id] = {
            "zone": zone_id,
            "position": position,
            "type": poi_type,
            "name": name,
            "description": description,
            "discovered": False
        }
        
        return {"success": True, "poi_id": poi_id}
    
    def discover_point_of_interest(self, poi_id):
        """Mark a point of interest as discovered by the player."""
        if poi_id in self.points_of_interest and not self.points_of_interest[poi_id]["discovered"]:
            self.points_of_interest[poi_id]["discovered"] = True
            
            poi_data = self.points_of_interest[poi_id]
            self.event_manager.trigger("poi_discovered", {
                "poi_id": poi_id,
                "name": poi_data["name"],
                "zone": poi_data["zone"]
            })
            
            # Check for related quests
            self.quest_system.update_poi_discovery(poi_id)
            
            return {"success": True, "poi": poi_data}
        
        return {"success": False, "error": "POI not found or already discovered"}
    
    def get_discovered_points_of_interest(self):
        """Get all points of interest discovered by the player."""
        return {
            poi_id: poi_data
            for poi_id, poi_data in self.points_of_interest.items()
            if poi_data["discovered"]
        }
    
    def update_weather(self, event_data=None):
        """Update weather conditions across all zones."""
        weather_types = ["clear", "cloudy", "rainy", "stormy", "foggy", "snowy"]
        
        for zone_id, zone_data in self.world_data["zones"].items():
            # Use zone characteristics to influence weather
            if "mountain" in zone_id:
                # Mountains more likely to have snow or clear weather
                weather_weights = [3, 1, 0, 1, 2, 5]  # Weights for each weather type
            elif "forest" in zone_id:
                # Forests more likely to have rain or fog
                weather_weights = [2, 2, 3, 1, 4, 0]
            elif "desert" in zone_id:
                # Deserts mostly clear with occasional storms
                weather_weights = [6, 2, 0, 1, 1, 0]
            else:
                # Default even distribution
                weather_weights = [1, 1, 1, 1, 1, 1]
            
            # Get weighted random weather
            weather = random.choices(weather_types, weights=weather_weights, k=1)[0]
            self.weather_conditions[zone_id] = weather
        
        self.event_manager.trigger("weather_updated", {
            "conditions": self.weather_conditions
        })
        
        return self.weather_conditions
    
    def on_zone_changed(self, event_data):
        """Handle zone change event."""
        # This method is called by the event system when a player changes zones
        player_id = event_data.get("player_id")
        new_zone = event_data.get("new_zone")
        
        # Check for points of interest nearby when entering a new zone
        self._check_nearby_points_of_interest(player_id, new_zone)
        
        # Update quest status for zone-related quests
        self.quest_system.update_zone_entry(new_zone)
    
    def on_world_event_started(self, event_data):
        """Handle world event start."""
        # This method is called by the event system when a world event starts
        pass
    
    def on_world_event_completed(self, event_data):
        """Handle world event completion."""
        event_id = event_data.get("event_id")
        
        # Remove the event from active events
        self.active_world_events = [
            event for event in self.active_world_events
            if event["id"] != event_id
        ]
    
    def on_poi_discovered(self, event_data):
        """Handle point of interest discovery."""
        # This method is called by the event system when a POI is discovered
        pass
    
    def _check_nearby_points_of_interest(self, player_id, zone_id):
        """Check if player is near any undiscovered points of interest."""
        # In a real implementation, this would use player's position
        # For this example, we're just simulating proximity detection
        for poi_id, poi_data in self.points_of_interest.items():
            if poi_data["zone"] == zone_id and not poi_data["discovered"]:
                # Random chance to discover POI when entering zone
                if random.random() < 0.3:  # 30% chance
                    self.discover_point_of_interest(poi_id)
    
    def _sync_player_map_data(self, player_id):
        """Sync player's map data with the server."""
        map_data = {
            "player_id": player_id,
            "current_zone": self.current_zone,
            "discovered_zones": list(self.discovered_zones),
            "unlocked_fast_travel": list(self.unlocked_fast_travel),
            "map_markers": self.map_markers,
            "discovered_pois": {
                poi_id: poi_data for poi_id, poi_data in self.points_of_interest.items()
                if poi_data["discovered"]
            }
        }
        
        try:
            self.server_sync.sync_data("player_map_data", map_data)
        except Exception as e:
            print(f"Error syncing player map data: {e}")
    
    def get_minimap_data(self, zone_id, player_position):
        """Get data for rendering the minimap UI."""
        # Return relevant map data for the minimap UI component
        if zone_id not in self.world_data["zones"]:
            return {"success": False, "error": "Invalid zone"}
            
        return {
            "success": True,
            "zone_name": self.world_data["zones"][zone_id]["name"],
            "weather": self.weather_conditions.get(zone_id, "clear"),
            "markers": self.get_map_markers_in_zone(zone_id),
            "points_of_interest": [
                poi for poi_id, poi in self.points_of_interest.items()
                if poi["zone"] == zone_id and poi["discovered"]
            ],
            "active_events": self.get_active_events_in_zone(zone_id)
        }