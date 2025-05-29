#!/usr/bin/env python3
"""
MOBA UI Module - Handles UI elements specific to MOBA game mode
This module provides UI elements like hero abilities, minimap, team stats,
item shop integration, and other MOBA-specific interface components.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple

# Core system imports
from core.modules.eventManager import EventManager
from core.modules.resourceManager import ResourceManager
from core.modules.timeManager import TimeManager

# UI system imports
from ui.interface.uiElement import UIElement
from ui.interface.mainMenu import MainMenu
from ui.interface.pauseMenu import PauseMenu
from ui.interface.shopInterface import ShopInterface

# MOBA game specific imports
from moba.logic.heroSystem import HeroSystem
from moba.logic.mobaMap import MobaMap
from moba.logic.roleManager import RoleManager


class AbilitySlot(UIElement):
    """UI element representing a hero ability slot."""
    
    def __init__(self, ability_id: str, icon_path: str, key_binding: str):
        """Initialize an ability slot.
        
        Args:
            ability_id: Unique identifier for the ability
            icon_path: Path to the ability icon
            key_binding: Keyboard key bound to this ability
        """
        super().__init__()
        self.ability_id = ability_id
        self.icon_path = icon_path
        self.key_binding = key_binding
        self.cooldown = 0
        self.max_cooldown = 0
        self.level = 0
        self.max_level = 4
        self.is_available = False
        self.is_selected = False
        self.is_passive = False
        self.mana_cost = 0
        self.tooltip = ""
    
    def update(self, delta_time: float):
        """Update the ability slot state.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if self.cooldown > 0:
            self.cooldown = max(0, self.cooldown - delta_time)
    
    def is_on_cooldown(self) -> bool:
        """Check if the ability is on cooldown.
        
        Returns:
            True if the ability is on cooldown, False otherwise
        """
        return self.cooldown > 0
    
    def get_cooldown_percentage(self) -> float:
        """Get the cooldown percentage.
        
        Returns:
            Cooldown percentage (0.0 to 1.0)
        """
        if self.max_cooldown <= 0:
            return 0.0
        return self.cooldown / self.max_cooldown
    
    def set_cooldown(self, cooldown_time: float):
        """Set the ability cooldown.
        
        Args:
            cooldown_time: Cooldown time in seconds
        """
        self.cooldown = cooldown_time
        self.max_cooldown = cooldown_time
    
    def use_ability(self) -> bool:
        """Attempt to use the ability.
        
        Returns:
            True if ability was used, False otherwise
        """
        if self.is_on_cooldown() or not self.is_available:
            return False
        
        # The actual ability usage would be handled by the hero system
        # This just updates the UI state
        return True
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the ability slot.
        
        Args:
            x: X position
            y: Y position
            width: Width of the slot
            height: Height of the slot
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class HeroPortrait(UIElement):
    """UI element showing the hero portrait with health and mana bars."""
    
    def __init__(self, hero_id: str, portrait_path: str):
        """Initialize a hero portrait.
        
        Args:
            hero_id: Unique identifier for the hero
            portrait_path: Path to the hero portrait image
        """
        super().__init__()
        self.hero_id = hero_id
        self.portrait_path = portrait_path
        self.health = 100
        self.max_health = 100
        self.mana = 100
        self.max_mana = 100
        self.level = 1
        self.experience = 0
        self.experience_to_level = 100
        self.status_effects = []
    
    def update_stats(self, health: int, max_health: int, mana: int, max_mana: int, 
                    level: int, experience: int, experience_to_level: int):
        """Update the hero stats.
        
        Args:
            health: Current health
            max_health: Maximum health
            mana: Current mana
            max_health: Maximum mana
            level: Current level
            experience: Current experience
            experience_to_level: Experience needed for next level
        """
        self.health = health
        self.max_health = max_health
        self.mana = mana
        self.max_mana = max_mana
        self.level = level
        self.experience = experience
        self.experience_to_level = experience_to_level
    
    def add_status_effect(self, effect_id: str, icon_path: str, duration: float):
        """Add a status effect to the hero.
        
        Args:
            effect_id: Unique identifier for the effect
            icon_path: Path to the effect icon
            duration: Duration of the effect in seconds
        """
        self.status_effects.append({
            "id": effect_id,
            "icon": icon_path,
            "duration": duration,
            "start_time": time.time()
        })
    
    def update(self, delta_time: float):
        """Update the hero portrait.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update status effects
        current_time = time.time()
        self.status_effects = [effect for effect in self.status_effects 
                              if current_time - effect["start_time"] < effect["duration"]]
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the hero portrait.
        
        Args:
            x: X position
            y: Y position
            width: Width of the portrait
            height: Height of the portrait
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class MinimapWidget(UIElement):
    """UI element showing the minimap with player positions and objectives."""
    
    def __init__(self, map_image_path: str, width: int, height: int):
        """Initialize the minimap widget.
        
        Args:
            map_image_path: Path to the minimap background image
            width: Width of the minimap
            height: Height of the minimap
        """
        super().__init__()
        self.map_image_path = map_image_path
        self.width = width
        self.height = height
        self.player_positions = {}  # Dict of player_id to (x, y) position
        self.ally_positions = {}    # Dict of ally_id to (x, y) position
        self.enemy_positions = {}   # Dict of enemy_id to (x, y) position
        self.objectives = {}        # Dict of objective_id to (x, y, active) status
        self.pings = []             # List of (x, y, type, time) pings
        self.vision_radius = 0.2    # Normalized vision radius (0.0 to 1.0)
        self.fog_of_war = True      # Whether fog of war is enabled
        self.show_objectives = True # Whether to show objectives
    
    def update_position(self, entity_id: str, x: float, y: float, entity_type: str = "player"):
        """Update an entity's position on the minimap.
        
        Args:
            entity_id: Unique identifier for the entity
            x: X position (normalized 0.0 to 1.0)
            y: Y position (normalized 0.0 to 1.0)
            entity_type: Type of entity (player, ally, enemy)
        """
        if entity_type == "player":
            self.player_positions[entity_id] = (x, y)
        elif entity_type == "ally":
            self.ally_positions[entity_id] = (x, y)
        elif entity_type == "enemy":
            self.enemy_positions[entity_id] = (x, y)
    
    def update_objective(self, objective_id: str, x: float, y: float, active: bool):
        """Update an objective's status on the minimap.
        
        Args:
            objective_id: Unique identifier for the objective
            x: X position (normalized 0.0 to 1.0)
            y: Y position (normalized 0.0 to 1.0)
            active: Whether the objective is active
        """
        self.objectives[objective_id] = (x, y, active)
    
    def add_ping(self, x: float, y: float, ping_type: str):
        """Add a ping to the minimap.
        
        Args:
            x: X position (normalized 0.0 to 1.0)
            y: Y position (normalized 0.0 to 1.0)
            ping_type: Type of ping (alert, assist, danger, etc.)
        """
        self.pings.append((x, y, ping_type, time.time()))
    
    def update(self, delta_time: float):
        """Update the minimap.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update pings (remove old ones)
        current_time = time.time()
        self.pings = [ping for ping in self.pings if current_time - ping[3] < 3.0]  # 3 seconds lifetime
    
    def render(self, x: int, y: int):
        """Render the minimap.
        
        Args:
            x: X position
            y: Y position
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass
    
    
def map_to_screen(self, map_x: float, map_y: float) -> Tuple[int, int]:
    """Convert map coordinates to screen coordinates.
        
    Args:
        map_x: X position on map (normalized 0.0 to 1.0)
        map_y: Y position on map (normalized 0.0 to 1.0)
            
    Returns:
        Tuple of (screen_x, screen_y) coordinates
    """
    # Convert normalized map coordinates to screen coordinates
    screen_x = self.origin_x + int(map_x * self.width)
    screen_y = self.origin_y + int(map_y * self.height)
    return (screen_x, screen_y)
class TeamScorePanel(UIElement):
    """UI element showing team scores, kills, and objectives."""
    
    def __init__(self):
        """Initialize the team score panel."""
        super().__init__()
        self.team_kills = {"ally": 0, "enemy": 0}
        self.team_objectives = {"ally": 0, "enemy": 0}
        self.match_time = 0
        self.team_gold = {"ally": 0, "enemy": 0}
        self.team_experience = {"ally": 0, "enemy": 0}
        self.player_stats = {}  # Dict of player_id to stats dict
    
    def update_team_stats(self, ally_kills: int, enemy_kills: int, 
                          ally_objectives: int, enemy_objectives: int,
                          ally_gold: int, enemy_gold: int,
                          ally_exp: int, enemy_exp: int):
        """Update team statistics.
        
        Args:
            ally_kills: Number of kills by ally team
            enemy_kills: Number of kills by enemy team
            ally_objectives: Number of objectives completed by ally team
            enemy_objectives: Number of objectives completed by enemy team
            ally_gold: Total gold earned by ally team
            enemy_gold: Total gold earned by enemy team
            ally_exp: Total experience earned by ally team
            enemy_exp: Total experience earned by enemy team
        """
        self.team_kills["ally"] = ally_kills
        self.team_kills["enemy"] = enemy_kills
        self.team_objectives["ally"] = ally_objectives
        self.team_objectives["enemy"] = enemy_objectives
        self.team_gold["ally"] = ally_gold
        self.team_gold["enemy"] = enemy_gold
        self.team_experience["ally"] = ally_exp
        self.team_experience["enemy"] = enemy_exp
    
    def update_player_stats(self, player_id: str, kills: int, deaths: int, 
                           assists: int, gold: int, cs: int):
        """Update statistics for a specific player.
        
        Args:
            player_id: Unique identifier for the player
            kills: Number of kills
            deaths: Number of deaths
            assists: Number of assists
            gold: Gold earned
            cs: Creep score (minions killed)
        """
        self.player_stats[player_id] = {
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "gold": gold,
            "cs": cs
        }
    
    def update_match_time(self, seconds: int):
        """Update the match time.
        
        Args:
            seconds: Match time in seconds
        """
        self.match_time = seconds
    
    def get_formatted_time(self) -> str:
        """Get the formatted match time.
        
        Returns:
            Formatted time string (MM:SS)
        """
        minutes = self.match_time // 60
        seconds = self.match_time % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the team score panel.
        
        Args:
            x: X position
            y: Y position
            width: Width of the panel
            height: Height of the panel
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class ItemInventoryPanel(UIElement):
    """UI element showing the player's item inventory."""
    
    def __init__(self, max_slots: int = 6):
        """Initialize the item inventory panel.
        
        Args:
            max_slots: Maximum number of item slots
        """
        super().__init__()
        self.max_slots = max_slots
        self.items = [None] * max_slots  # List of item_id or None
        self.gold = 0
        self.shop_button_active = False
    
    def set_item(self, slot_index: int, item_id: str = None):
        """Set an item in a specific slot.
        
        Args:
            slot_index: Index of the slot to set
            item_id: ID of the item to set, or None to clear
        """
        if slot_index < 0 or slot_index >= self.max_slots:
            return
        
        self.items[slot_index] = item_id
    
    def get_item(self, slot_index: int) -> Optional[str]:
        """Get the item in a specific slot.
        
        Args:
            slot_index: Index of the slot to get
            
        Returns:
            Item ID or None if slot is empty
        """
        if slot_index < 0 or slot_index >= self.max_slots:
            return None
        
        return self.items[slot_index]
    
    def use_item(self, slot_index: int) -> bool:
        """Use the item in a specific slot.
        
        Args:
            slot_index: Index of the slot to use
            
        Returns:
            True if item was used, False otherwise
        """
        item_id = self.get_item(slot_index)
        if not item_id:
            return False
        
        # The actual item usage would be handled by the item system
        # This just updates the UI state
        return True
    
    def update_gold(self, gold: int):
        """Update the player's gold.
        
        Args:
            gold: Player's current gold
        """
        self.gold = gold
    
    def toggle_shop_button(self, active: bool):
        """Toggle the shop button.
        
        Args:
            active: Whether the shop button is active
        """
        self.shop_button_active = active
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the item inventory panel.
        
        Args:
            x: X position
            y: Y position
            width: Width of the panel
            height: Height of the panel
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class ChatPanel(UIElement):
    """UI element showing the in-game chat."""
    
    def __init__(self, max_messages: int = 10):
        """Initialize the chat panel.
        
        Args:
            max_messages: Maximum number of chat messages to display
        """
        super().__init__()
        self.max_messages = max_messages
        self.messages = []  # List of (sender, message, team_only, timestamp) tuples
        self.input_active = False
        self.input_text = ""
        self.team_chat_mode = True  # True for team chat, False for all chat
        self.visible = True
        self.fade_timer = 0
        self.fade_duration = 5.0  # Time until chat fades when inactive
    
    def add_message(self, sender: str, message: str, team_only: bool = False):
        """Add a chat message.
        
        Args:
            sender: Name of the message sender
            message: Message content
            team_only: Whether the message is team-only
        """
        self.messages.append((sender, message, team_only, time.time()))
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        
        # Reset fade timer
        self.fade_timer = 0
    
    def activate_input(self):
        """Activate chat input."""
        self.input_active = True
        self.input_text = ""
        self.fade_timer = 0
        self.visible = True
    
    def deactivate_input(self):
        """Deactivate chat input."""
        self.input_active = False
        self.input_text = ""
    
    def toggle_team_chat(self):
        """Toggle between team and all chat."""
        self.team_chat_mode = not self.team_chat_mode
    
    def update(self, delta_time: float):
        """Update the chat panel.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update fade timer if chat is inactive
        if not self.input_active and self.messages:
            self.fade_timer += delta_time
            
            # Auto-hide chat after fade duration
            if self.fade_timer > self.fade_duration:
                self.visible = False
    
    def handle_input(self, input_event):
        """Handle input events.
        
        Args:
            input_event: Input event to handle
        """
        if not self.is_visible:
            return
            
        # Handle chat input
        if self.chat_panel.input_active:
            self.chat_panel.handle_input(input_event)
            return  # Don't process other inputs when chat is active
        
        # Toggle scoreboard
        if input_event.type == "key_press" and input_event.key == "tab":
            self.toggle_scoreboard()
        
        # Activate chat
        elif input_event.type == "key_press" and input_event.key == "enter":
            self.chat_panel.activate_input()
        
        # Use abilities
        elif input_event.type == "key_press" and input_event.key in ["q", "w", "e", "r"]:
            ability_index = {"q": 0, "w": 1, "e": 2, "r": 3}.get(input_event.key.lower(), -1)
            if ability_index >= 0 and ability_index < len(self.ability_slots):
                ability_slot = self.ability_slots[ability_index]
                if ability_slot.use_ability():
                    # Trigger ability use event - the game logic will handle the actual ability usage
                    self.event_manager.trigger("ability_use_requested", ability_slot.ability_id)
        
        # Use items
        elif input_event.type == "key_press" and input_event.key in ["1", "2", "3", "4", "5", "6"]:
            item_index = int(input_event.key) - 1
            if self.item_inventory.use_item(item_index):
                # Trigger item use event - the game logic will handle the actual item usage
                item_id = self.item_inventory.get_item(item_index)
                self.event_manager.trigger("item_use_requested", item_id, item_index)
        
        # Process minimap clicks
        elif input_event.type == "mouse_click" and input_event.button == "left":
            # Check if click is on minimap
            if self.minimap and hasattr(self.minimap, "is_point_inside") and self.minimap.is_point_inside(input_event.x, input_event.y):
                # Get minimap screen position (would come from layout system in a real game)
                minimap_x = input_event.screen_width - self.minimap.width - 20
                minimap_y = input_event.screen_height - self.minimap.height - 20
                map_x, map_y = self.minimap.screen_to_map(input_event.x, input_event.y, minimap_x, minimap_y)
                self.event_manager.trigger("minimap_click", map_x, map_y)
        
        # Process minimap pings
        elif input_event.type == "mouse_click" and input_event.button == "right":
            # Check if click is on minimap
            if self.minimap and hasattr(self.minimap, "is_point_inside") and self.minimap.is_point_inside(input_event.x, input_event.y):
                # Get minimap screen position (would come from layout system in a real game)
                minimap_x = input_event.screen_width - self.minimap.width - 20
                minimap_y = input_event.screen_height - self.minimap.height - 20
                map_x, map_y = self.minimap.screen_to_map(input_event.x, input_event.y, minimap_x, minimap_y)
                ping_type = "alert"  # Default ping type
                self.event_manager.trigger("minimap_ping_requested", map_x, map_y, ping_type)
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the chat panel.
        
        Args:
            x: X position
            y: Y position
            width: Width of the panel
            height: Height of the panel
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class DeathRecapPanel(UIElement):
    """UI element showing details about player death."""
    
    def __init__(self):
        """Initialize the death recap panel."""
        super().__init__()
        self.visible = False
        self.death_time = 0
        self.respawn_time = 0
        self.killer_id = ""
        self.killer_name = ""
        self.damage_sources = []  # List of (source_name, damage, ability_name) tuples
        self.total_damage = 0
    
    def show_recap(self, killer_id: str, killer_name: str, respawn_time: int):
        """Show the death recap.
        
        Args:
            killer_id: ID of the killer
            killer_name: Name of the killer
            respawn_time: Time until respawn in seconds
        """
        self.visible = True
        self.death_time = time.time()
        self.respawn_time = respawn_time
        self.killer_id = killer_id
        self.killer_name = killer_name
        self.damage_sources = []
        self.total_damage = 0
    
    def add_damage_source(self, source_name: str, damage: int, ability_name: str):
        """Add a damage source to the recap.
        
        Args:
            source_name: Name of the damage source
            damage: Amount of damage
            ability_name: Name of the ability that caused the damage
        """
        self.damage_sources.append((source_name, damage, ability_name))
        self.total_damage += damage
        
        # Sort damage sources by damage amount (descending)
        self.damage_sources.sort(key=lambda x: x[1], reverse=True)
    
    def get_remaining_time(self) -> int:
        """Get the remaining time until respawn.
        
        Returns:
            Remaining time in seconds
        """
        elapsed = time.time() - self.death_time
        remaining = max(0, self.respawn_time - elapsed)
        return int(remaining)
    
    def close(self):
        """Close the death recap panel."""
        self.visible = False
    
    def update(self, delta_time: float):
        """Update the death recap panel.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Auto-close when respawn time is up
        if self.visible and self.get_remaining_time() <= 0:
            self.close()
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the death recap panel.
        
        Args:
            x: X position
            y: Y position
            width: Width of the panel
            height: Height of the panel
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class ScoreboardPanel(UIElement):
    """UI element showing the full scoreboard with all players."""
    
    def __init__(self):
        """Initialize the scoreboard panel."""
        super().__init__()
        self.visible = False
        self.player_stats = {}  # Dict of player_id to stats dict
        self.team_stats = {"ally": {}, "enemy": {}}
    
    def show(self):
        """Show the scoreboard."""
        self.visible = True
    
    def hide(self):
        """Hide the scoreboard."""
        self.visible = False
    
    def toggle(self):
        """Toggle the scoreboard visibility."""
        self.visible = not self.visible
    
    def update_player_stats(self, player_id: str, team: str, hero_id: str, player_name: str,
                           kills: int, deaths: int, assists: int, 
                           gold: int, cs: int, level: int, items: List[str]):
        """Update statistics for a specific player.
        
        Args:
            player_id: Unique identifier for the player
            team: Team the player is on ("ally" or "enemy")
            hero_id: ID of the hero the player is using
            player_name: Display name of the player
            kills: Number of kills
            deaths: Number of deaths
            assists: Number of assists
            gold: Gold earned
            cs: Creep score (minions killed)
            level: Player level
            items: List of item IDs the player has
        """
        self.player_stats[player_id] = {
            "team": team,
            "hero_id": hero_id,
            "name": player_name,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "gold": gold,
            "cs": cs,
            "level": level,
            "items": items
        }
    
    def update_team_stats(self, team: str, kills: int, objectives: int, 
                         towers: int, gold: int):
        """Update statistics for a team.
        
        Args:
            team: Team to update ("ally" or "enemy")
            kills: Number of kills
            objectives: Number of objectives completed
            towers: Number of towers destroyed
            gold: Total gold earned
        """
        self.team_stats[team] = {
            "kills": kills,
            "objectives": objectives,
            "towers": towers,
            "gold": gold
        }
    
    def render(self, x: int, y: int, width: int, height: int):
        """Render the scoreboard panel.
        
        Args:
            x: X position
            y: Y position
            width: Width of the panel
            height: Height of the panel
        """
        # This would be implemented by the game's UI system
        # Placeholder for rendering logic
        pass


class MobaUI:
    """Main class for the MOBA UI, managing all MOBA-specific UI elements."""
    
    def __init__(self, event_manager: EventManager, resource_manager: ResourceManager, 
                time_manager: TimeManager, hero_system: HeroSystem, 
                moba_map: MobaMap, shop_interface: ShopInterface = None):
        """Initialize the MOBA UI.
        
        Args:
            event_manager: Event manager for handling UI events
            resource_manager: Resource manager for loading UI assets
            time_manager: Time manager for handling time-based UI events
            hero_system: Hero system for accessing hero data
            moba_map: MOBA map for accessing map data
            shop_interface: Shop interface for buying items
        """
        self.event_manager = event_manager
        self.resource_manager = resource_manager
        self.time_manager = time_manager
        self.hero_system = hero_system
        self.moba_map = moba_map
        self.shop_interface = shop_interface
        self.logger = logging.getLogger('MobaUI')
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize UI elements
        self.ability_slots = []
        self.hero_portrait = None
        self.minimap = None
        self.team_score_panel = TeamScorePanel()
        self.item_inventory = ItemInventoryPanel()
        self.chat_panel = ChatPanel()
        self.death_recap = DeathRecapPanel()
        self.scoreboard = ScoreboardPanel()
        
        # UI state
        self.is_visible = False
        self.player_id = ""
        self.hero_id = ""
        self.show_tooltips = True
        
        # Register event listeners
        self.event_manager.add_listener("show_moba_ui", self.show)
        self.event_manager.add_listener("hide_moba_ui", self.hide)
        self.event_manager.add_listener("toggle_scoreboard", self.toggle_scoreboard)
        self.event_manager.add_listener("player_died", self.on_player_died)
        self.event_manager.add_listener("ability_used", self.on_ability_used)
        self.event_manager.add_listener("item_purchased", self.on_item_purchased)
        self.event_manager.add_listener("chat_message_received", self.on_chat_message)
        self.event_manager.add_listener("minimap_ping", self.on_minimap_ping)
    
    def _load_config(self) -> Dict:
        """Load UI configuration from file.
        
        Returns:
            Dictionary containing UI configuration
        """
        try:
            with open("configs/data/mobaUIConfig.json", 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            self.logger.error(f"Failed to load MOBA UI config: {e}")
            return {}
    
    def initialize(self, player_id: str, hero_id: str):
        """Initialize the UI for a specific player and hero.
        
        Args:
            player_id: ID of the player
            hero_id: ID of the hero the player is using
        """
        self.player_id = player_id
        self.hero_id = hero_id
        
        # Initialize hero portrait
        hero_data = self.hero_system.get_hero_data(hero_id)
        if hero_data:
            self.hero_portrait = HeroPortrait(hero_id, hero_data["portrait_path"])
        
        # Initialize ability slots
        self.ability_slots = []
        if hero_data and "abilities" in hero_data:
            key_bindings = ["Q", "W", "E", "R"]
            for i, ability in enumerate(hero_data["abilities"]):
                if i < len(key_bindings):
                    slot = AbilitySlot(ability["id"], ability["icon_path"], key_bindings[i])
                    slot.tooltip = ability.get("tooltip", "")
                    slot.is_passive = ability.get("passive", False)
                    slot.mana_cost = ability.get("mana_cost", 0)
                    slot.level = 0  # Start with no abilities leveled
                    self.ability_slots.append(slot)
        
        # Initialize minimap
        map_data = self.moba_map.get_map_data()
        if map_data:
            self.minimap = MinimapWidget(map_data["minimap_path"], 200, 200)
        
        # Initialize other UI elements
        self.team_score_panel = TeamScorePanel()
        self.item_inventory = ItemInventoryPanel()
        self.chat_panel = ChatPanel()
        self.death_recap = DeathRecapPanel()
        self.scoreboard = ScoreboardPanel()
        
        self.is_visible = True
        self.logger.info(f"MOBA UI initialized for player {player_id} with hero {hero_id}")
    
    def show(self):
        """Show the MOBA UI."""
        self.is_visible = True
        self.event_manager.trigger("moba_ui_shown")
    
    def hide(self):
        """Hide the MOBA UI."""
        self.is_visible = False
        self.event_manager.trigger("moba_ui_hidden")
    
    def toggle_scoreboard(self):
        """Toggle the scoreboard visibility."""
        self.scoreboard.toggle()
    
    def on_player_died(self, killer_id: str, killer_name: str, respawn_time: int, damage_sources: List[Dict]):
        """Handle player death event.
        
        Args:
            killer_id: ID of the killer
            killer_name: Name of the killer
            respawn_time: Time until respawn in seconds
            damage_sources: List of damage source dictionaries
        """
        self.death_recap.show_recap(killer_id, killer_name, respawn_time)
        
        for source in damage_sources:
            self.death_recap.add_damage_source(
                source["name"],
                source["damage"],
                source["ability"]
            )
    
    def on_ability_used(self, ability_id: str, cooldown: float):
        """Handle ability used event.
        
        Args:
            ability_id: ID of the ability used
            cooldown: Cooldown time in seconds
        """
        for slot in self.ability_slots:
            if slot.ability_id == ability_id:
                slot.set_cooldown(cooldown)
                break
    
    def on_item_purchased(self, item_id: str, slot_index: int):
        """Handle item purchased event.
        
        Args:
            item_id: ID of the purchased item
            slot_index: Inventory slot index
        """
        self.item_inventory.set_item(slot_index, item_id)
    
    def on_chat_message(self, sender: str, message: str, team_only: bool):
        """Handle chat message received event.
        
        Args:
            sender: Name of the message sender
            message: Message content
            team_only: Whether the message is team-only
        """
        self.chat_panel.add_message(sender, message, team_only)
    
    def on_minimap_ping(self, x: float, y: float, ping_type: str):
        """Handle minimap ping event.
        
        Args:
            x: X position (normalized 0.0 to 1.0)
            y: Y position (normalized 0.0 to 1.0)
            ping_type: Type of ping (alert, assist, danger, etc.)
        """
        if self.minimap:
            self.minimap.add_ping(x, y, ping_type)
    
    def update_hero_stats(self, health: int, max_health: int, mana: int, max_mana: int, 
                         level: int, experience: int, experience_to_level: int):
        """Update hero statistics.
        
        Args:
            health: Current health
            max_health: Maximum health
            mana: Current mana
            max_mana: Maximum mana
            level: Current level
            experience: Current experience
            experience_to_level: Experience needed for next level
        """
        if self.hero_portrait:
            self.hero_portrait.update_stats(
                health, max_health, mana, max_mana,
                level, experience, experience_to_level
            )
    
    def update_abilities(self, abilities: List[Dict]):
        """Update ability information.
        
        Args:
            abilities: List of ability data dictionaries
        """
        for ability_data in abilities:
            ability_id = ability_data["id"]
            for slot in self.ability_slots:
                if slot.ability_id == ability_id:
                    slot.level = ability_data.get("level", 0)
                    slot.is_available = ability_data.get("available", False)
                    if "cooldown" in ability_data:
                        slot.cooldown = ability_data["cooldown"]
                        slot.max_cooldown = ability_data.get("max_cooldown", slot.cooldown)
                    break
    
    def update_gold(self, gold: int):
        """Update player gold.
        
        Args:
            gold: Player's current gold
        """
        self.item_inventory.update_gold(gold)
    
    def update_scoreboard(self, players: List[Dict], team_data: Dict):
        """Update scoreboard data.
        
        Args:
            players: List of player data dictionaries
            team_data: Dictionary of team data
        """
        for player in players:
            self.scoreboard.update_player_stats(
                player["id"],
                player["team"],
                player["hero_id"],
                player["name"],
                player["kills"],
                player["deaths"],
                player["assists"],
                player["gold"],
                player["cs"],
                player["level"],
                player["items"]
            )
        
        for team, data in team_data.items():
            self.scoreboard.update_team_stats(
                team,
                data["kills"],
                data["objectives"],
                data["towers"],
                data["gold"]
            )
    
    def update_team_scores(self, ally_kills: int, enemy_kills: int, 
                          ally_objectives: int, enemy_objectives: int,
                          ally_gold: int, enemy_gold: int,
                          ally_exp: int, enemy_exp: int,
                          match_time: int):
        """Update team score panel.
        
        Args:
            ally_kills: Number of kills by ally team
            enemy_kills: Number of kills by enemy team
            ally_objectives: Number of objectives completed by ally team
            enemy_objectives: Number of objectives completed by enemy team
            ally_gold: Total gold earned by ally team
            enemy_gold: Total gold earned by enemy team
            ally_exp: Total experience earned by ally team
            enemy_exp: Total experience earned by enemy team
            match_time: Match time in seconds
        """
        self.team_score_panel.update_team_stats(
            ally_kills, enemy_kills,
            ally_objectives, enemy_objectives,
            ally_gold, enemy_gold,
            ally_exp, enemy_exp
        )
        self.team_score_panel.update_match_time(match_time)
    
    def update_minimap_positions(self, positions: Dict):
        """Update entity positions on the minimap.
        
        Args:
            positions: Dictionary of entity positions
        """
        if not self.minimap:
            return
            
        for entity_type, entities in positions.items():
            for entity_id, pos in entities.items():
                x, y = pos
                self.minimap.update_position(entity_id, x, y, entity_type)
    
    def update_minimap_objectives(self, objectives: Dict):
        """Update objectives on the minimap.
        
        Args:
            objectives: Dictionary of objective data
        """
        if not self.minimap:
            return
            
        for obj_id, obj_data in objectives.items():
            x, y, active = obj_data
            self.minimap.update_objective(obj_id, x, y, active)
    
    def handle_input(self, input_event):
        """Handle input events.
        
        Args:
            input_event: Input event to handle
        """
        if not self.is_visible:
            return
            
        # Handle chat input
        if self.chat_panel.input_active:
            self.chat_panel.handle_input(input_event)
            return  # Don't process other inputs when chat is active
        
        # Toggle scoreboard
        if input_event.type == "key_press" and input_event.key == "tab":
            self.toggle_scoreboard()
        
        # Activate chat
        elif input_event.type == "key_press" and input_event.key == "enter":
            self.chat_panel.activate_input()
        
        # Use abilities
        elif input_event.type == "key_press" and input_event.key in ["q", "w", "e", "r"]:
            ability_index = {"q": 0, "w": 1, "e": 2, "r": 3}.get(input_event.key.lower(), -1)
            if ability_index >= 0 and ability_index < len(self.ability_slots):
                ability_slot = self.ability_slots[ability_index]
                if ability_slot.use_ability():
                    # Trigger ability use event - the game logic will handle the actual ability usage
                    self.event_manager.trigger("ability_use_requested", ability_slot.ability_id)
        
        # Use items
        elif input_event.type == "key_press" and input_event.key in ["1", "2", "3", "4", "5", "6"]:
            item_index = int(input_event.key) - 1
            if self.item_inventory.use_item(item_index):
                # Trigger item use event - the game logic will handle the actual item usage
                item_id = self.item_inventory.get_item(item_index)
                self.event_manager.trigger("item_use_requested", item_id, item_index)
        
        # Process minimap clicks
        elif input_event.type == "mouse_click" and input_event.button == "left":
            # Check if click is on minimap
            if self.minimap and self.minimap.is_point_inside(input_event.x, input_event.y):
                map_x, map_y = self.minimap.screen_to_map(input_event.x, input_event.y)
                self.event_manager.trigger("minimap_click", map_x, map_y)
        
        # Process minimap pings
        elif input_event.type == "mouse_click" and input_event.button == "right":
            # Check if click is on minimap
            if self.minimap and self.minimap.is_point_inside(input_event.x, input_event.y):
                map_x, map_y = self.minimap.screen_to_map(input_event.x, input_event.y)
                ping_type = "alert"  # Default ping type
                self.event_manager.trigger("minimap_ping_requested", map_x, map_y, ping_type)
    
    def update(self, delta_time: float):
        """Update all UI elements.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if not self.is_visible:
            return
        
        # Update all UI elements
        for slot in self.ability_slots:
            slot.update(delta_time)
        
        if self.hero_portrait:
            self.hero_portrait.update(delta_time)
        
        if self.minimap:
            self.minimap.update(delta_time)
        
        self.chat_panel.update(delta_time)
        self.death_recap.update(delta_time)
    
    def render(self, screen_width: int, screen_height: int):
        """Render the MOBA UI.
        
        Args:
            screen_width: Width of the screen
            screen_height: Height of the screen
        """
        if not self.is_visible:
            return
        
        # Layout configuration (would normally be loaded from config)
        ability_bar_x = screen_width // 2 - 200
        ability_bar_y = screen_height - 100
        ability_slot_size = 50
        ability_slot_spacing = 10
        
        portrait_x = ability_bar_x - 100
        portrait_y = ability_bar_y - 25
        portrait_size = 100
        
        minimap_size = 200
        minimap_x = screen_width - minimap_size - 20
        minimap_y = screen_height - minimap_size - 20
        
        team_score_x = 20
        team_score_y = 20
        team_score_width = screen_width - 40
        team_score_height = 30
        
        inventory_x = ability_bar_x + (ability_slot_size + ability_slot_spacing) * 4 + 20
        inventory_y = ability_bar_y
        inventory_slot_size = 40
        inventory_slot_spacing = 5
        
        chat_x = 20
        chat_y = screen_height - 200
        chat_width = 300
        chat_height = 150
        
        # Render UI elements
        if self.hero_portrait:
            self.hero_portrait.render(portrait_x, portrait_y, portrait_size, portrait_size)
        
        # Render ability slots
        for i, slot in enumerate(self.ability_slots):
            x = ability_bar_x + i * (ability_slot_size + ability_slot_spacing)
            slot.render(x, ability_bar_y, ability_slot_size, ability_slot_size)
        
        # Render minimap
        if self.minimap:
            self.minimap.render(minimap_x, minimap_y)
        
        # Render team score panel
        self.team_score_panel.render(team_score_x, team_score_y, team_score_width, team_score_height)
        
        # Render inventory
        self.item_inventory.render(inventory_x, inventory_y, 
                                 inventory_slot_size * 6 + inventory_slot_spacing * 5, 
                                 inventory_slot_size)
        
        # Render chat panel if visible
        if self.chat_panel.visible:
            self.chat_panel.render(chat_x, chat_y, chat_width, chat_height)
        
        # Render death recap if visible
        if self.death_recap.visible:
            death_recap_x = screen_width // 2 - 200
            death_recap_y = screen_height // 2 - 150
            self.death_recap.render(death_recap_x, death_recap_y, 400, 300)
        
        # Render scoreboard if visible
        if self.scoreboard.visible:
            scoreboard_x = screen_width // 2 - 300
            scoreboard_y = screen_height // 2 - 200
            self.scoreboard.render(scoreboard_x, scoreboard_y, 600, 400)
    
    def cleanup(self):
        """Clean up resources and event listeners."""
        # Unregister event listeners
        self.event_manager.remove_listener("show_moba_ui", self.show)
        self.event_manager.remove_listener("hide_moba_ui", self.hide)
        self.event_manager.remove_listener("toggle_scoreboard", self.toggle_scoreboard)
        self.event_manager.remove_listener("player_died", self.on_player_died)
        self.event_manager.remove_listener("ability_used", self.on_ability_used)
        self.event_manager.remove_listener("item_purchased", self.on_item_purchased)
        self.event_manager.remove_listener("chat_message_received", self.on_chat_message)
        self.event_manager.remove_listener("minimap_ping", self.on_minimap_ping)
        
        self.logger.info("MOBA UI cleaned up")


class MobaHUDManager:
    """Manager class for the MOBA HUD (Heads-Up Display)."""
    
    def __init__(self, event_manager: EventManager, moba_ui: MobaUI):
        """Initialize the MOBA HUD manager.
        
        Args:
            event_manager: Event manager for handling HUD events
            moba_ui: MOBA UI instance
        """
        self.event_manager = event_manager
        self.moba_ui = moba_ui
        self.logger = logging.getLogger('MobaHUDManager')
        
        # HUD state
        self.is_visible = True
        self.hud_scale = 1.0
        self.minimap_scale = 1.0
        self.show_ally_health_bars = True
        self.show_enemy_health_bars = True
        self.show_neutral_health_bars = True
        self.ping_volume = 0.5
        self.ping_sound_enabled = True
        
        # Register event listeners
        self.event_manager.add_listener("toggle_hud", self.toggle_hud)
        self.event_manager.add_listener("set_hud_scale", self.set_hud_scale)
        self.event_manager.add_listener("set_minimap_scale", self.set_minimap_scale)
        self.event_manager.add_listener("toggle_health_bars", self.toggle_health_bars)
        self.event_manager.add_listener("set_ping_volume", self.set_ping_volume)
        self.event_manager.add_listener("toggle_ping_sound", self.toggle_ping_sound)
    
    def toggle_hud(self):
        """Toggle HUD visibility."""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.moba_ui.show()
        else:
            self.moba_ui.hide()
        self.logger.debug(f"HUD visibility toggled to {self.is_visible}")
    
    def set_hud_scale(self, scale: float):
        """Set HUD scale.
        
        Args:
            scale: Scale factor (0.5 to 1.5)
        """
        self.hud_scale = max(0.5, min(1.5, scale))
        self.logger.debug(f"HUD scale set to {self.hud_scale}")
        self.event_manager.trigger("hud_scale_changed", self.hud_scale)
    
    def set_minimap_scale(self, scale: float):
        """Set minimap scale.
        
        Args:
            scale: Scale factor (0.5 to 1.5)
        """
        self.minimap_scale = max(0.5, min(1.5, scale))
        self.logger.debug(f"Minimap scale set to {self.minimap_scale}")
        self.event_manager.trigger("minimap_scale_changed", self.minimap_scale)
    
    def toggle_health_bars(self, entity_type: str):
        """Toggle health bars for specific entity types.
        
        Args:
            entity_type: Type of entities to toggle health bars for
                         ("ally", "enemy", "neutral")
        """
        if entity_type == "ally":
            self.show_ally_health_bars = not self.show_ally_health_bars
            self.logger.debug(f"Ally health bars toggled to {self.show_ally_health_bars}")
        elif entity_type == "enemy":
            self.show_enemy_health_bars = not self.show_enemy_health_bars
            self.logger.debug(f"Enemy health bars toggled to {self.show_enemy_health_bars}")
        elif entity_type == "neutral":
            self.show_neutral_health_bars = not self.show_neutral_health_bars
            self.logger.debug(f"Neutral health bars toggled to {self.show_neutral_health_bars}")
    
    def set_ping_volume(self, volume: float):
        """Set ping sound volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.ping_volume = max(0.0, min(1.0, volume))
        self.logger.debug(f"Ping volume set to {self.ping_volume}")
    
    def toggle_ping_sound(self):
        """Toggle ping sounds."""
        self.ping_sound_enabled = not self.ping_sound_enabled
        self.logger.debug(f"Ping sound toggled to {self.ping_sound_enabled}")
    
    def get_hud_config(self) -> Dict:
        """Get current HUD configuration.
        
        Returns:
            Dictionary containing HUD configuration
        """
        return {
            "hud_visible": self.is_visible,
            "hud_scale": self.hud_scale,
            "minimap_scale": self.minimap_scale,
            "show_ally_health_bars": self.show_ally_health_bars,
            "show_enemy_health_bars": self.show_enemy_health_bars,
            "show_neutral_health_bars": self.show_neutral_health_bars,
            "ping_volume": self.ping_volume,
            "ping_sound_enabled": self.ping_sound_enabled
        }
    
    def save_hud_config(self):
        """Save HUD configuration to file."""
        config = self.get_hud_config()
        try:
            with open("configs/data/hudConfig.json", 'w') as f:
                json.dump(config, f, indent=4)
            self.logger.info("HUD configuration saved")
        except Exception as e:
            self.logger.error(f"Failed to save HUD configuration: {e}")
    
    def load_hud_config(self):
        """Load HUD configuration from file."""
        try:
            with open("configs/data/hudConfig.json", 'r') as f:
                config = json.load(f)
            
            self.is_visible = config.get("hud_visible", True)
            self.hud_scale = config.get("hud_scale", 1.0)
            self.minimap_scale = config.get("minimap_scale", 1.0)
            self.show_ally_health_bars = config.get("show_ally_health_bars", True)
            self.show_enemy_health_bars = config.get("show_enemy_health_bars", True)
            self.show_neutral_health_bars = config.get("show_neutral_health_bars", True)
            self.ping_volume = config.get("ping_volume", 0.5)
            self.ping_sound_enabled = config.get("ping_sound_enabled", True)
            
            self.logger.info("HUD configuration loaded")
        except Exception as e:
            self.logger.error(f"Failed to load HUD configuration: {e}")
    
    def cleanup(self):
        """Clean up resources and event listeners."""
        # Save configuration before cleanup
        self.save_hud_config()
        
        # Unregister event listeners
        self.event_manager.remove_listener("toggle_hud", self.toggle_hud)
        self.event_manager.remove_listener("set_hud_scale", self.set_hud_scale)
        self.event_manager.remove_listener("set_minimap_scale", self.set_minimap_scale)
        self.event_manager.remove_listener("toggle_health_bars", self.toggle_health_bars)
        self.event_manager.remove_listener("set_ping_volume", self.set_ping_volume)
        self.event_manager.remove_listener("toggle_ping_sound", self.toggle_ping_sound)
        
        self.logger.info("MOBA HUD Manager cleaned up")


if __name__ == "__main__":
    # Simple test code
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('MobaUITest')
    logger.info("Testing MOBA UI module")
    
    # This would be initialized properly in a real game
    event_manager = EventManager()
    resource_manager = ResourceManager()
    time_manager = TimeManager()
    hero_system = HeroSystem(event_manager, resource_manager)
    moba_map = MobaMap(event_manager, resource_manager)
    shop_interface = ShopInterface(event_manager, resource_manager)
    
    # Initialize MOBA UI
    moba_ui = MobaUI(event_manager, resource_manager, time_manager, 
                    hero_system, moba_map, shop_interface)
    
    # Initialize HUD manager
    hud_manager = MobaHUDManager(event_manager, moba_ui)
    
    logger.info("MOBA UI test completed")