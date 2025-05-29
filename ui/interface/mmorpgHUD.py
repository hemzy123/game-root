#!/usr/bin/env python3
"""
MMORPG HUD Module - Handles the heads-up display for the MMORPG game mode
This module provides the UI elements specific to the MMORPG gameplay experience,
including health bars, mana, experience, minimap, skill bars, inventory, etc.
"""

import json
import logging
import math
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Callable

# Core system imports
from core.modules.eventManager import EventManager
from core.modules.resourceManager import ResourceManager
from core.modules.animationManager import AnimationManager
from core.modules.audioManager import AudioManager

# Player and character imports
from backend.player.playerManager import PlayerManager
from backend.game.characterManager import CharacterManager
from backend.game.gameStateManager import GameStateManager
from backend.game.questManager import QuestManager
from backend.game.inventoryManager import InventoryManager
from backend.game.skillManager import SkillManager

# UI imports
from ui.interface.uiElement import UIElement
from ui.interface.uiTheme import UITheme
from ui.widgets.healthBar import HealthBar
from ui.widgets.manaBar import ManaBar
from ui.widgets.experienceBar import ExperienceBar
from ui.widgets.minimap import Minimap
from ui.widgets.actionBar import ActionBar
from ui.widgets.buffIndicator import BuffIndicator
from ui.widgets.chatBox import ChatBox
from ui.widgets.partyFrame import PartyFrame
from ui.widgets.targetFrame import TargetFrame
from ui.widgets.questTracker import QuestTracker
from ui.widgets.tooltipManager import TooltipManager


class HUDMode(Enum):
    """Enumeration of different HUD display modes."""
    MINIMAL = 0      # Shows only essential elements
    STANDARD = 1     # Shows regular gameplay elements
    COMBAT = 2       # Shows combat-focused elements
    SOCIAL = 3       # Shows social and party elements
    CUSTOMIZED = 4   # User-customized layout


class ElementVisibility(Enum):
    """Enumeration of visibility states for HUD elements."""
    HIDDEN = 0       # Element is not visible
    TRANSPARENT = 1  # Element is semi-transparent
    VISIBLE = 2      # Element is fully visible
    AUTO = 3         # Element visibility is determined by context


class MMORPGHUD(UIElement):
    """HUD interface class for MMORPG game mode."""
    
    def __init__(self, event_manager: EventManager, resource_manager: ResourceManager, 
                 animation_manager: AnimationManager, audio_manager: AudioManager,
                 player_manager: PlayerManager, character_manager: CharacterManager,
                 quest_manager: QuestManager, inventory_manager: InventoryManager,
                 skill_manager: SkillManager, game_state_manager: GameStateManager):
        """Initialize the MMORPG HUD.
        
        Args:
            event_manager: Event manager for handling HUD events
            resource_manager: Resource manager for loading HUD assets
            animation_manager: Animation manager for HUD animations
            audio_manager: Audio manager for HUD sounds
            player_manager: Player manager for accessing player data
            character_manager: Character manager for accessing character data
            quest_manager: Quest manager for tracking quests
            inventory_manager: Inventory manager for managing items
            skill_manager: Skill manager for managing skills and abilities
            game_state_manager: Game state manager for tracking game state
        """
        super().__init__()
        self.event_manager = event_manager
        self.resource_manager = resource_manager
        self.animation_manager = animation_manager
        self.audio_manager = audio_manager
        self.player_manager = player_manager
        self.character_manager = character_manager
        self.quest_manager = quest_manager
        self.inventory_manager = inventory_manager
        self.skill_manager = skill_manager
        self.game_state_manager = game_state_manager
        self.logger = logging.getLogger('MMORPGHUD')
        
        # HUD state
        self.is_visible = False
        self.current_mode = HUDMode.STANDARD
        self.visibility_settings = {}  # Element ID to ElementVisibility mapping
        self.element_positions = {}    # Element ID to position mapping
        self.element_sizes = {}        # Element ID to size mapping
        self.is_combat_active = False
        self.is_in_safe_zone = True
        self.custom_layouts = {}       # Layout name to custom layout mapping
        self.active_layout = "default"
        
        # HUD elements
        self.elements = {}  # Dictionary of HUD elements by ID
        
        # Tooltip management
        self.tooltip_manager = TooltipManager()
        self.hover_element = None
        
        # Register event listeners
        self.event_manager.add_listener("show_hud", self.show)
        self.event_manager.add_listener("hide_hud", self.hide)
        self.event_manager.add_listener("enter_combat", self.enter_combat)
        self.event_manager.add_listener("exit_combat", self.exit_combat)
        self.event_manager.add_listener("enter_safe_zone", self.enter_safe_zone)
        self.event_manager.add_listener("exit_safe_zone", self.exit_safe_zone)
        self.event_manager.add_listener("player_health_changed", self.update_player_health)
        self.event_manager.add_listener("player_mana_changed", self.update_player_mana)
        self.event_manager.add_listener("player_exp_changed", self.update_player_experience)
        self.event_manager.add_listener("quest_updated", self.update_quest_tracker)
        self.event_manager.add_listener("inventory_updated", self.update_inventory)
        self.event_manager.add_listener("target_changed", self.update_target)
        self.event_manager.add_listener("buff_applied", self.add_buff)
        self.event_manager.add_listener("buff_removed", self.remove_buff)
        self.event_manager.add_listener("chat_message_received", self.add_chat_message)
        self.event_manager.add_listener("party_updated", self.update_party_frames)
        self.event_manager.add_listener("ability_cooldown_start", self.start_ability_cooldown)
        self.event_manager.add_listener("ability_cooldown_end", self.end_ability_cooldown)
        self.event_manager.add_listener("minimap_updated", self.update_minimap)
        
        # Load HUD configuration
        self.load_config()
        
        # Initialize HUD elements
        self.initialize_elements()
    
    def _apply_custom_layout(self, layout_name: str) -> None:
        """
        Apply a custom HUD layout by updating element positions, sizes, and visibility.
        
        Args:
            layout_name (str): The name of the custom layout to apply.
        """
        if layout_name not in self.custom_layouts:
            self.logger.warning(f"Custom layout '{layout_name}' not found.")
            return

        layout = self.custom_layouts[layout_name]

        # Apply positions
        for element_id, position in layout.get("positions", {}).items():
            if element_id in self.elements:
                self.elements[element_id].set_position(position)

        # Apply sizes
        for element_id, size in layout.get("sizes", {}).items():
            if element_id in self.elements:
                self.elements[element_id].set_size(size)

        # Apply visibility settings
        for element_id, visibility in layout.get("visibility", {}).items():
            if element_id in self.elements:
                try:
                    # Assuming ElementVisibility is an Enum or similar
                    self.set_element_visibility(element_id, ElementVisibility(visibility))
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid visibility value '{visibility}' for element '{element_id}'.")

        self.logger.info(f"Applied custom layout: '{layout_name}'")
        self.active_layout = layout_name

    
    def load_config(self):
        """Load HUD configuration from files."""
        try:
            # Load HUD theme
            with open("configs/data/uiThemes.json", 'r') as f:
                themes_data = json.load(f)
                self.ui_theme = UITheme(themes_data.get("mmorpg_hud", {}))
            
            # Load HUD layout
            with open("configs/data/hudLayouts.json", 'r') as f:
                layouts_data = json.load(f)
                self.element_positions = layouts_data.get("default", {}).get("positions", {})
                self.element_sizes = layouts_data.get("default", {}).get("sizes", {})
                self.visibility_settings = layouts_data.get("default", {}).get("visibility", {})
                self.custom_layouts = layouts_data.get("custom", {})
            
            # Load user preferences if available
            player_id = self.player_manager.get_player_id()
            user_config_path = f"configs/players/{player_id}/hud_config.json"
            if self.resource_manager.file_exists(user_config_path):
                with open(user_config_path, 'r') as f:
                    user_config = json.load(f)
                    self.active_layout = user_config.get("active_layout", "default")
                    
                    # Apply user-defined layout if it exists
                    if self.active_layout in self.custom_layouts:
                        layout = self.custom_layouts[self.active_layout]
                        self.element_positions.update(layout.get("positions", {}))
                        self.element_sizes.update(layout.get("sizes", {}))
                        self.visibility_settings.update(layout.get("visibility", {}))
            
            self.logger.info("HUD configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load HUD configuration: {e}")
            
            # Set default values if configuration loading fails
            self.element_positions = {}
            self.element_sizes = {}
            self.visibility_settings = {}
    
    def initialize_elements(self):
        """Initialize all HUD elements."""
        try:
            # Player status elements
            self._initialize_player_frame()
            self._initialize_resource_bars()
            self._initialize_minimap()
            self._initialize_action_bars()
            self._initialize_buff_indicators()
            self._initialize_target_frame()
            self._initialize_party_frames()
            self._initialize_quest_tracker()
            self._initialize_chat_box()
            self._initialize_exp_bar()
            
            # Apply initial visibility settings
            for element_id, visibility in self.visibility_settings.items():
                if element_id in self.elements:
                    try:
                        self.set_element_visibility(element_id, ElementVisibility(visibility))
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid visibility value for element {element_id}")
            
            self.logger.info("HUD elements initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize HUD elements: {e}")
    
    def _initialize_player_frame(self):
        """Initialize the player frame element."""
        player_frame = TargetFrame(
            "player_frame",
            self.ui_theme.get_frame_style("player"),
            is_player=True
        )
        
        # Set position and size if defined in config
        if "player_frame" in self.element_positions:
            player_frame.set_position(self.element_positions["player_frame"])
        else:
            player_frame.set_position({"x": 0.05, "y": 0.1, "anchor": "top_left"})
            
        if "player_frame" in self.element_sizes:
            player_frame.set_size(self.element_sizes["player_frame"])
        
        # Add to elements dictionary
        self.elements["player_frame"] = player_frame
        
        # Update with player data
        self._update_player_frame()
    
    def _initialize_resource_bars(self):
        """Initialize health and mana bars."""
        # Health bar
        health_bar = HealthBar(
            "health_bar",
            self.ui_theme.get_bar_style("health")
        )
        
        if "health_bar" in self.element_positions:
            health_bar.set_position(self.element_positions["health_bar"])
        else:
            health_bar.set_position({"x": 0.2, "y": 0.95, "anchor": "bottom_left"})
            
        if "health_bar" in self.element_sizes:
            health_bar.set_size(self.element_sizes["health_bar"])
        
        self.elements["health_bar"] = health_bar
        
        # Mana bar
        mana_bar = ManaBar(
            "mana_bar",
            self.ui_theme.get_bar_style("mana")
        )
        
        if "mana_bar" in self.element_positions:
            mana_bar.set_position(self.element_positions["mana_bar"])
        else:
            mana_bar.set_position({"x": 0.2, "y": 0.98, "anchor": "bottom_left"})
            
        if "mana_bar" in self.element_sizes:
            mana_bar.set_size(self.element_sizes["mana_bar"])
        
        self.elements["mana_bar"] = mana_bar
        
        # Update bars with initial values
        self._update_resource_bars()
    
    def _initialize_minimap(self):
        """Initialize the minimap."""
        minimap = Minimap(
            "minimap",
            self.ui_theme.get_frame_style("minimap")
        )
        
        if "minimap" in self.element_positions:
            minimap.set_position(self.element_positions["minimap"])
        else:
            minimap.set_position({"x": 0.95, "y": 0.1, "anchor": "top_right"})
            
        if "minimap" in self.element_sizes:
            minimap.set_size(self.element_sizes["minimap"])
        
        self.elements["minimap"] = minimap
        
        # Load initial map data
        current_map = self.game_state_manager.get_current_map_id()
        minimap_data = self.resource_manager.get_minimap_data(current_map)
        if minimap_data:
            minimap.set_map_data(minimap_data)
    
    def _initialize_action_bars(self):
        """Initialize action bars for abilities and items."""
        # Main action bar
        main_action_bar = ActionBar(
            "main_action_bar",
            self.ui_theme.get_bar_style("action"),
            slot_count=12
        )
        
        if "main_action_bar" in self.element_positions:
            main_action_bar.set_position(self.element_positions["main_action_bar"])
        else:
            main_action_bar.set_position({"x": 0.5, "y": 0.95, "anchor": "bottom_center"})
            
        if "main_action_bar" in self.element_sizes:
            main_action_bar.set_size(self.element_sizes["main_action_bar"])
        
        self.elements["main_action_bar"] = main_action_bar
        
        # Secondary action bar
        secondary_action_bar = ActionBar(
            "secondary_action_bar",
            self.ui_theme.get_bar_style("action_secondary"),
            slot_count=12
        )
        
        if "secondary_action_bar" in self.element_positions:
            secondary_action_bar.set_position(self.element_positions["secondary_action_bar"])
        else:
            secondary_action_bar.set_position({"x": 0.5, "y": 0.9, "anchor": "bottom_center"})
            
        if "secondary_action_bar" in self.element_sizes:
            secondary_action_bar.set_size(self.element_sizes["secondary_action_bar"])
        
        self.elements["secondary_action_bar"] = secondary_action_bar
        
        # Side action bar for additional abilities
        side_action_bar = ActionBar(
            "side_action_bar",
            self.ui_theme.get_bar_style("action_side"),
            slot_count=12,
            vertical=True
        )
        
        if "side_action_bar" in self.element_positions:
            side_action_bar.set_position(self.element_positions["side_action_bar"])
        else:
            side_action_bar.set_position({"x": 0.95, "y": 0.5, "anchor": "right_center"})
            
        if "side_action_bar" in self.element_sizes:
            side_action_bar.set_size(self.element_sizes["side_action_bar"])
        
        self.elements["side_action_bar"] = side_action_bar
        
        # Load initial action bar data
        self._update_action_bars()
    
    def _initialize_buff_indicators(self):
        """Initialize buff indicators."""
        # Player buffs
        player_buffs = BuffIndicator(
            "player_buffs",
            self.ui_theme.get_frame_style("buffs"),
            is_debuff=False
        )
        
        if "player_buffs" in self.element_positions:
            player_buffs.set_position(self.element_positions["player_buffs"])
        else:
            player_buffs.set_position({"x": 0.2, "y": 0.2, "anchor": "top_left"})
            
        if "player_buffs" in self.element_sizes:
            player_buffs.set_size(self.element_sizes["player_buffs"])
        
        self.elements["player_buffs"] = player_buffs
        
        # Player debuffs
        player_debuffs = BuffIndicator(
            "player_debuffs",
            self.ui_theme.get_frame_style("debuffs"),
            is_debuff=True
        )
        
        if "player_debuffs" in self.element_positions:
            player_debuffs.set_position(self.element_positions["player_debuffs"])
        else:
            player_debuffs.set_position({"x": 0.3, "y": 0.2, "anchor": "top_left"})
            
        if "player_debuffs" in self.element_sizes:
            player_debuffs.set_size(self.element_sizes["player_debuffs"])
        
        self.elements["player_debuffs"] = player_debuffs
        
        # Target buffs
        target_buffs = BuffIndicator(
            "target_buffs",
            self.ui_theme.get_frame_style("target_buffs"),
            is_debuff=False
        )
        
        if "target_buffs" in self.element_positions:
            target_buffs.set_position(self.element_positions["target_buffs"])
        else:
            target_buffs.set_position({"x": 0.7, "y": 0.2, "anchor": "top_right"})
            
        if "target_buffs" in self.element_sizes:
            target_buffs.set_size(self.element_sizes["target_buffs"])
        
        self.elements["target_buffs"] = target_buffs
        
        # Target debuffs
        target_debuffs = BuffIndicator(
            "target_debuffs",
            self.ui_theme.get_frame_style("target_debuffs"),
            is_debuff=True
        )
        
        if "target_debuffs" in self.element_positions:
            target_debuffs.set_position(self.element_positions["target_debuffs"])
        else:
            target_debuffs.set_position({"x": 0.8, "y": 0.2, "anchor": "top_right"})
            
        if "target_debuffs" in self.element_sizes:
            target_debuffs.set_size(self.element_sizes["target_debuffs"])
        
        self.elements["target_debuffs"] = target_debuffs
    
    def _initialize_target_frame(self):
        """Initialize the target frame."""
        target_frame = TargetFrame(
            "target_frame",
            self.ui_theme.get_frame_style("target"),
            is_player=False
        )
        
        if "target_frame" in self.element_positions:
            target_frame.set_position(self.element_positions["target_frame"])
        else:
            target_frame.set_position({"x": 0.95, "y": 0.1, "anchor": "top_right"})
            
        if "target_frame" in self.element_sizes:
            target_frame.set_size(self.element_sizes["target_frame"])
        
        self.elements["target_frame"] = target_frame
    
    def _initialize_party_frames(self):
        """Initialize party member frames."""
        party_frame = PartyFrame(
            "party_frame",
            self.ui_theme.get_frame_style("party"),
            max_members=5  # Standard party size
        )
        
        if "party_frame" in self.element_positions:
            party_frame.set_position(self.element_positions["party_frame"])
        else:
            party_frame.set_position({"x": 0.05, "y": 0.3, "anchor": "left_center"})
            
        if "party_frame" in self.element_sizes:
            party_frame.set_size(self.element_sizes["party_frame"])
        
        self.elements["party_frame"] = party_frame
        
        # Update party frames with initial data
        party_data = self.player_manager.get_party_data()
        if party_data:
            party_frame.update_party(party_data)
    
    def _initialize_quest_tracker(self):
        """Initialize the quest tracker."""
        quest_tracker = QuestTracker(
            "quest_tracker",
            self.ui_theme.get_frame_style("quest_tracker")
        )
        
        if "quest_tracker" in self.element_positions:
            quest_tracker.set_position(self.element_positions["quest_tracker"])
        else:
            quest_tracker.set_position({"x": 0.95, "y": 0.5, "anchor": "right_center"})
            
        if "quest_tracker" in self.element_sizes:
            quest_tracker.set_size(self.element_sizes["quest_tracker"])
        
        self.elements["quest_tracker"] = quest_tracker
        
        # Load active quests
        active_quests = self.quest_manager.get_active_quests()
        if active_quests:
            quest_tracker.set_quests(active_quests)
    
    def _initialize_chat_box(self):
        """Initialize the chat box."""
        chat_box = ChatBox(
            "chat_box",
            self.ui_theme.get_frame_style("chat_box")
        )
        
        if "chat_box" in self.element_positions:
            chat_box.set_position(self.element_positions["chat_box"])
        else:
            chat_box.set_position({"x": 0.05, "y": 0.9, "anchor": "bottom_left"})
            
        if "chat_box" in self.element_sizes:
            chat_box.set_size(self.element_sizes["chat_box"])
        
        self.elements["chat_box"] = chat_box
        
        # Add default channels
        chat_box.add_channel("General")
        chat_box.add_channel("Combat")
        chat_box.add_channel("Party")
        chat_box.add_channel("Guild")
        chat_box.add_channel("Trade")
        chat_box.add_channel("System")
        
        # Set active channel
        chat_box.set_active_channel("General")
    
    def _initialize_exp_bar(self):
        """Initialize the experience bar."""
        exp_bar = ExperienceBar(
            "exp_bar",
            self.ui_theme.get_bar_style("experience")
        )
        
        if "exp_bar" in self.element_positions:
            exp_bar.set_position(self.element_positions["exp_bar"])
        else:
            exp_bar.set_position({"x": 0.5, "y": 0.99, "anchor": "bottom_center"})
            
        if "exp_bar" in self.element_sizes:
            exp_bar.set_size(self.element_sizes["exp_bar"])
        
        self.elements["exp_bar"] = exp_bar
        
        # Update with initial experience data
        player_data = self.player_manager.get_player_data()
        if player_data and "experience" in player_data:
            current_exp = player_data["experience"].get("current", 0)
            max_exp = player_data["experience"].get("next_level", 100)
            level = player_data["experience"].get("level", 1)
            exp_bar.update(current_exp, max_exp, level)
    
    def _update_player_frame(self):
        """Update player frame with current player data."""
        if not self.player_manager.is_player_loaded() or "player_frame" not in self.elements:
            return
        
        player_data = self.player_manager.get_player_data()
        player_character = self.character_manager.get_player_character()
        
        if player_data and player_character:
            player_frame = self.elements["player_frame"]
            
            player_frame.set_name(player_character.get("name", "Player"))
            player_frame.set_level(player_character.get("level", 1))
            player_frame.set_class(player_character.get("class", "Unknown"))
            player_frame.set_portrait(player_character.get("portrait", "default_portrait"))
            
            # Set health and mana
            health = player_character.get("health", {})
            player_frame.set_health(health.get("current", 100), health.get("max", 100))
            
            mana = player_character.get("mana", {})
            player_frame.set_mana(mana.get("current", 100), mana.get("max", 100))
    
    def _update_resource_bars(self):
        """Update health and mana bars with current values."""
        if not self.player_manager.is_player_loaded():
            return
        
        player_character = self.character_manager.get_player_character()
        
        if player_character:
            # Update health bar
            if "health_bar" in self.elements:
                health = player_character.get("health", {})
                health_bar = self.elements["health_bar"]
                health_bar.update(health.get("current", 100), health.get("max", 100))
            
            # Update mana bar
            if "mana_bar" in self.elements:
                mana = player_character.get("mana", {})
                mana_bar = self.elements["mana_bar"]
                mana_bar.update(mana.get("current", 100), mana.get("max", 100))
    
    def _update_action_bars(self):
        """Update action bars with current abilities and items."""
        if not self.player_manager.is_player_loaded() or not self.skill_manager:
            return
        
        # Get abilities and items
        abilities = self.skill_manager.get_active_abilities()
        quick_items = self.inventory_manager.get_quick_items()
        
        # Update main action bar
        if "main_action_bar" in self.elements and abilities:
            main_bar = self.elements["main_action_bar"]
            for slot, ability in abilities.get("primary", {}).items():
                if 0 <= int(slot) < main_bar.get_slot_count():
                    main_bar.set_slot_content(int(slot), ability)
        
        # Update secondary action bar
        if "secondary_action_bar" in self.elements and abilities:
            secondary_bar = self.elements["secondary_action_bar"]
            for slot, ability in abilities.get("secondary", {}).items():
                if 0 <= int(slot) < secondary_bar.get_slot_count():
                    secondary_bar.set_slot_content(int(slot), ability)
        
        # Update side action bar
        if "side_action_bar" in self.elements:
            side_bar = self.elements["side_action_bar"]
            # First, add extra abilities
            for slot, ability in abilities.get("extra", {}).items():
                if 0 <= int(slot) < side_bar.get_slot_count():
                    side_bar.set_slot_content(int(slot), ability)
            
            # Then add quick items
            for slot, item in quick_items.items():
                slot_index = int(slot) + 6  # Use second half of side bar for items
                if 0 <= slot_index < side_bar.get_slot_count():
                    side_bar.set_slot_content(slot_index, item)
    
    def show(self):
        """Show the HUD."""
        if self.is_visible:
            return
        
        self.logger.info("Showing MMORPG HUD")
        self.is_visible = True
        
        # Update all elements with current data
        self._update_player_frame()
        self._update_resource_bars()
        self._update_action_bars()
        
        # Trigger HUD shown event
        self.event_manager.trigger("hud_shown", {})
    
    def hide(self):
        """Hide the HUD."""
        if not self.is_visible:
            return
        
        self.logger.info("Hiding MMORPG HUD")
        self.is_visible = False
        
        # Trigger HUD hidden event
        self.event_manager.trigger("hud_hidden", {})
    
    def set_mode(self, mode: HUDMode):
        """Set the HUD display mode.
        
        Args:
            mode: HUD mode to set
        """
        if mode == self.current_mode:
            return
        
        self.logger.info(f"Changing HUD mode to: {mode.name}")
        self.current_mode = mode
        
        # Apply mode-specific settings
        if mode == HUDMode.MINIMAL:
            # Show only essential elements
            self._apply_visibility_preset("minimal")
        elif mode == HUDMode.COMBAT:
            # Show combat-focused elements
            self._apply_visibility_preset("combat")
        elif mode == HUDMode.SOCIAL:
            # Show social and party elements
            self._apply_visibility_preset("social")
        elif mode == HUDMode.STANDARD:
            # Show standard gameplay elements
            self._apply_visibility_preset("standard")
        elif mode == HUDMode.CUSTOMIZED:
            # Use custom layout if available, otherwise use standard
            custom_layout_name = self.player_manager.get_setting("hud_custom_layout", "default")
            if custom_layout_name in self.custom_layouts:
                self._apply_custom_layout(custom_layout_name)
            else:
                self._apply_visibility_preset("standard")
    
    def _apply_visibility_preset(self, preset_name: str):
        """Apply a visibility preset to HUD elements.
        
        Args:
            preset_name: Name of the preset to apply
        """
        preset_path = f"configs/data/hudPresets/{preset_name}.json"
        try:
            with open(preset_path, 'r') as f:
                preset_data = json.load(f)
                visibility_settings = preset_data.get("visibility", {})
                
                # Apply visibility settings
                for element_id, visibility in visibility_settings.items():
                    if element_id in self.elements:
                        try:
                            self.set_element_visibility(element_id, ElementVisibility(visibility))
                        except (ValueError, TypeError):
                            self.logger.warning(f"Invalid visibility value for element {element_id}")
                
                self.logger.debug(f"Applied visibility preset: {preset_name}")
        except Exception as e:
            self.logger.error(f"Failed to apply visibility preset {preset_name}: {e}")
    
    
def set_element_visibility(self, element_id: str, visibility: ElementVisibility):
    """Set the visibility of a HUD element.
    
    Args:
        element_id: ID of the element to update
        visibility: Visibility state to set
    """
    if element_id not in self.elements:
        self.logger.warning(f"Element {element_id} not found")
        return
    
    element = self.elements[element_id]
    
    if visibility == ElementVisibility.HIDDEN:
        element.hide()
    elif visibility == ElementVisibility.TRANSPARENT:
        element.set_opacity(0.5)
        element.show()
    elif visibility == ElementVisibility.VISIBLE:
        element.set_opacity(1.0)
        element.show()
    elif visibility == ElementVisibility.AUTO:
        # AUTO visibility depends on context
        if self.is_combat_active and element_id in ["target_frame", "player_buffs", "player_debuffs"]:
            element.set_opacity(1.0)
            element.show()
        elif not self.is_combat_active and element_id in ["combat_log"]:
            element.hide()
        else:
            element.set_opacity(1.0)
            element.show()
    
    # Update visibility settings
    self.visibility_settings[element_id] = visibility.value

def save_custom_layout(self, layout_name: str):
    """Save the current HUD layout as a custom layout.
    
    Args:
        layout_name: Name to save the layout as
    """
    # Collect current positions
    positions = {}
    sizes = {}
    visibility = {}
    
    for element_id, element in self.elements.items():
        positions[element_id] = element.get_position()
        sizes[element_id] = element.get_size()
        
        # Get visibility state
        if not element.is_visible():
            visibility[element_id] = ElementVisibility.HIDDEN.value
        elif element.get_opacity() < 1.0:
            visibility[element_id] = ElementVisibility.TRANSPARENT.value
        else:
            visibility[element_id] = ElementVisibility.VISIBLE.value
    
    # Create layout data
    layout_data = {
        "positions": positions,
        "sizes": sizes,
        "visibility": visibility
    }
    
    # Save to custom layouts
    self.custom_layouts[layout_name] = layout_data
    
    # Save to file
    try:
        with open("configs/data/hudLayouts.json", 'r') as f:
            layouts_data = json.load(f)
        
        # Update custom layouts
        if "custom" not in layouts_data:
            layouts_data["custom"] = {}
        
        layouts_data["custom"][layout_name] = layout_data
        
        with open("configs/data/hudLayouts.json", 'w') as f:
            json.dump(layouts_data, f, indent=2)
        
        # Update player preferences
        player_id = self.player_manager.get_player_id()
        user_config_path = f"configs/players/{player_id}/hud_config.json"
        
        user_config = {"active_layout": layout_name}
        if self.resource_manager.file_exists(user_config_path):
            try:
                with open(user_config_path, 'r') as f:
                    existing_config = json.load(f)
                    user_config.update(existing_config)
                    user_config["active_layout"] = layout_name
            except Exception:
                pass
        
        with open(user_config_path, 'w') as f:
            json.dump(user_config, f, indent=2)
        
        self.logger.info(f"Saved custom layout: {layout_name}")
        self.active_layout = layout_name
        
        # Trigger layout saved event
        self.event_manager.trigger("hud_layout_saved", {"layout_name": layout_name})
        
        return True
    except Exception as e:
        self.logger.error(f"Failed to save custom layout: {e}")
        return False

def enter_combat(self):
    """Handle entering combat state."""
    if self.is_combat_active:
        return
    
    self.logger.debug("Entering combat mode")
    self.is_combat_active = True
    
    # Show combat-specific elements
    for element_id in ["target_frame", "player_buffs", "player_debuffs", "target_buffs", "target_debuffs"]:
        if element_id in self.elements and self.visibility_settings.get(element_id) == ElementVisibility.AUTO.value:
            self.elements[element_id].show()
    
    # Enable combat channel in chat
    if "chat_box" in self.elements:
        self.elements["chat_box"].enable_channel("Combat")
    
    # Play combat enter sound
    self.audio_manager.play_sound("ui_combat_enter")
    
    # Flash screen edge with red
    self.animation_manager.play_screen_effect("combat_enter")

def exit_combat(self):
    """Handle exiting combat state."""
    if not self.is_combat_active:
        return
    
    self.logger.debug("Exiting combat mode")
    self.is_combat_active = False
    
    # Hide combat-specific elements if in AUTO mode
    for element_id in ["target_frame", "player_buffs", "player_debuffs", "target_buffs", "target_debuffs"]:
        if element_id in self.elements and self.visibility_settings.get(element_id) == ElementVisibility.AUTO.value:
            self.elements[element_id].hide()
    
    # Reset target if needed
    if self.character_manager.get_target_type() == "enemy":
        self.character_manager.clear_target()
        if "target_frame" in self.elements:
            self.elements["target_frame"].clear()
    
    # Play combat exit sound
    self.audio_manager.play_sound("ui_combat_exit")

def enter_safe_zone(self):
    """Handle entering a safe zone."""
    if self.is_in_safe_zone:
        return
    
    self.logger.debug("Entering safe zone")
    self.is_in_safe_zone = True
    
    # Update minimap status
    if "minimap" in self.elements:
        self.elements["minimap"].set_safe_zone(True)
    
    # Play safe zone enter sound
    self.audio_manager.play_sound("ui_safe_zone_enter")
    
    # Add system message
    if "chat_box" in self.elements:
        self.elements["chat_box"].add_message("System", "You have entered a safe zone.")

def exit_safe_zone(self):
    """Handle exiting a safe zone."""
    if not self.is_in_safe_zone:
        return
    
    self.logger.debug("Exiting safe zone")
    self.is_in_safe_zone = False
    
    # Update minimap status
    if "minimap" in self.elements:
        self.elements["minimap"].set_safe_zone(False)
    
    # Play safe zone exit sound
    self.audio_manager.play_sound("ui_safe_zone_exit")
    
    # Add system message
    if "chat_box" in self.elements:
        self.elements["chat_box"].add_message("System", "You have left a safe zone.")

def update_player_health(self, event_data: Dict):
    """Update player health display.
    
    Args:
        event_data: Event data containing health information
    """
    current_health = event_data.get("current", 0)
    max_health = event_data.get("max", 100)
    
    # Update health bar
    if "health_bar" in self.elements:
        self.elements["health_bar"].update(current_health, max_health)
    
    # Update player frame
    if "player_frame" in self.elements:
        self.elements["player_frame"].set_health(current_health, max_health)
    
    # Update party frame if player is in a party
    if "party_frame" in self.elements:
        player_id = self.player_manager.get_player_id()
        self.elements["party_frame"].update_member_health(player_id, current_health, max_health)
    
    # Play low health warning if below threshold
    if current_health / max_health < 0.2 and "health_bar" in self.elements:
        self.elements["health_bar"].pulse_warning()
        
        # Play warning sound if not already playing
        if not self.audio_manager.is_sound_playing("ui_low_health_loop"):
            self.audio_manager.play_sound("ui_low_health_loop", loop=True)
    elif current_health / max_health >= 0.2 and self.audio_manager.is_sound_playing("ui_low_health_loop"):
        self.audio_manager.stop_sound("ui_low_health_loop")

def update_player_mana(self, event_data: Dict):
    """Update player mana display.
    
    Args:
        event_data: Event data containing mana information
    """
    current_mana = event_data.get("current", 0)
    max_mana = event_data.get("max", 100)
    
    # Update mana bar
    if "mana_bar" in self.elements:
        self.elements["mana_bar"].update(current_mana, max_mana)
    
    # Update player frame
    if "player_frame" in self.elements:
        self.elements["player_frame"].set_mana(current_mana, max_mana)
    
    # Update party frame if player is in a party
    if "party_frame" in self.elements:
        player_id = self.player_manager.get_player_id()
        self.elements["party_frame"].update_member_mana(player_id, current_mana, max_mana)

def update_player_experience(self, event_data: Dict):
    """Update player experience display.
    
    Args:
        event_data: Event data containing experience information
    """
    current_exp = event_data.get("current", 0)
    max_exp = event_data.get("next_level", 100)
    level = event_data.get("level", 1)
    
    # Update experience bar
    if "exp_bar" in self.elements:
        self.elements["exp_bar"].update(current_exp, max_exp, level)
    
    # If player leveled up, show level up animation
    if event_data.get("leveled_up", False):
        self.animation_manager.play_screen_effect("level_up")
        self.audio_manager.play_sound("ui_level_up")
        
        if "chat_box" in self.elements:
            self.elements["chat_box"].add_message("System", f"Congratulations! You have reached level {level}!")

def update_quest_tracker(self, event_data: Dict):
    """Update quest tracker display.
    
    Args:
        event_data: Event data containing quest information
    """
    if "quest_tracker" not in self.elements:
        return
    
    quest_id = event_data.get("quest_id")
    if not quest_id:
        return
    
    # Get updated quest data
    quest_data = self.quest_manager.get_quest(quest_id)
    if not quest_data:
        return
    
    # Update quest in tracker
    self.elements["quest_tracker"].update_quest(quest_data)
    
    # If quest completed, show notification
    if quest_data.get("status") == "completed" and event_data.get("status_changed", False):
        self.animation_manager.play_notification("quest_completed", quest_data.get("name", "Quest"))
        self.audio_manager.play_sound("ui_quest_complete")

def update_inventory(self, event_data: Dict):
    """Update inventory-related displays.
    
    Args:
        event_data: Event data containing inventory information
    """
    # Update action bars with any changed quick items
    quick_items = self.inventory_manager.get_quick_items()
    
    if "side_action_bar" in self.elements:
        side_bar = self.elements["side_action_bar"]
        for slot, item in quick_items.items():
            slot_index = int(slot) + 6  # Use second half of side bar for items
            if 0 <= slot_index < side_bar.get_slot_count():
                side_bar.set_slot_content(slot_index, item)
    
    # If a new item was added, show notification
    if event_data.get("action") == "add" and event_data.get("item"):
        item = event_data["item"]
        quality = item.get("quality", "common")
        
        # Only show notifications for uncommon+ items
        if quality != "common":
            self.animation_manager.play_notification("item_acquired", item.get("name", "Item"))
            
            # Play sound based on item quality
            sound_name = f"ui_item_{quality}"
            self.audio_manager.play_sound(sound_name)

def update_target(self, event_data: Dict):
    """Update target display.
    
    Args:
        event_data: Event data containing target information
    """
    target_type = event_data.get("type")
    target_id = event_data.get("id")
    
    if target_type is None or target_id is None:
        # Clear target
        if "target_frame" in self.elements:
            self.elements["target_frame"].clear()
        
        if "target_buffs" in self.elements:
            self.elements["target_buffs"].clear()
        
        if "target_debuffs" in self.elements:
            self.elements["target_debuffs"].clear()
        
        return
    
    # Get target data
    target_data = None
    if target_type == "npc" or target_type == "enemy":
        target_data = self.character_manager.get_npc(target_id)
    elif target_type == "player":
        target_data = self.character_manager.get_player(target_id)
    
    if not target_data or "target_frame" not in self.elements:
        return
    
    # Update target frame
    target_frame = self.elements["target_frame"]
    target_frame.set_name(target_data.get("name", "Unknown"))
    target_frame.set_level(target_data.get("level", 1))
    
    if target_type == "player":
        target_frame.set_class(target_data.get("class", "Unknown"))
    else:
        target_frame.set_type(target_data.get("creature_type", "Unknown"))
    
    target_frame.set_portrait(target_data.get("portrait", "default_portrait"))
    
    # Set health and mana
    health = target_data.get("health", {})
    target_frame.set_health(health.get("current", 100), health.get("max", 100))
    
    mana = target_data.get("mana", {})
    target_frame.set_mana(mana.get("current", 100), mana.get("max", 100))
    
    # Set hostility indicator
    if target_type == "enemy":
        target_frame.set_hostile(True)
    elif target_type == "npc":
        target_frame.set_hostile(False)
    
    # Update target buffs/debuffs
    if "target_buffs" in self.elements and "buffs" in target_data:
        self.elements["target_buffs"].set_buffs(target_data["buffs"])
    
    if "target_debuffs" in self.elements and "debuffs" in target_data:
        self.elements["target_debuffs"].set_buffs(target_data["debuffs"])
    
    # Play target selection sound
    if target_type == "enemy":
        self.audio_manager.play_sound("ui_target_enemy")
    elif target_type == "npc":
        self.audio_manager.play_sound("ui_target_npc")
    elif target_type == "player":
        self.audio_manager.play_sound("ui_target_player")

def add_buff(self, event_data: Dict):
    """Handle buff applied event.
    
    Args:
        event_data: Event data containing buff information
    """
    target_type = event_data.get("target_type")
    buff_data = event_data.get("buff")
    
    if not buff_data:
        return
    
    if target_type == "player":
        # Add to player buffs
        if "player_buffs" in self.elements and not buff_data.get("is_debuff", False):
            self.elements["player_buffs"].add_buff(buff_data)
        
        # Add to player debuffs
        if "player_debuffs" in self.elements and buff_data.get("is_debuff", False):
            self.elements["player_debuffs"].add_buff(buff_data)
        
        # Play sound based on buff type
        if buff_data.get("is_debuff", False):
            self.audio_manager.play_sound("ui_debuff_applied")
        else:
            self.audio_manager.play_sound("ui_buff_applied")
    
    elif target_type == "target":
        # Add to target buffs
        if "target_buffs" in self.elements and not buff_data.get("is_debuff", False):
            self.elements["target_buffs"].add_buff(buff_data)
        
        # Add to target debuffs
        if "target_debuffs" in self.elements and buff_data.get("is_debuff", False):
            self.elements["target_debuffs"].add_buff(buff_data)

def remove_buff(self, event_data: Dict):
    """Handle buff removed event.
    
    Args:
        event_data: Event data containing buff information
    """
    target_type = event_data.get("target_type")
    buff_id = event_data.get("buff_id")
    
    if not buff_id:
        return
    
    if target_type == "player":
        # Try to remove from both player buffs and debuffs
        if "player_buffs" in self.elements:
            self.elements["player_buffs"].remove_buff(buff_id)
        
        if "player_debuffs" in self.elements:
            self.elements["player_debuffs"].remove_buff(buff_id)
    
    elif target_type == "target":
        # Try to remove from both target buffs and debuffs
        if "target_buffs" in self.elements:
            self.elements["target_buffs"].remove_buff(buff_id)
        
        if "target_debuffs" in self.elements:
            self.elements["target_debuffs"].remove_buff(buff_id)

def add_chat_message(self, event_data: Dict):
    """Handle chat message received event.
    
    Args:
        event_data: Event data containing message information
    """
    if "chat_box" not in self.elements:
        return
    
    channel = event_data.get("channel", "General")
    sender = event_data.get("sender", "")
    message = event_data.get("message", "")
    
    self.elements["chat_box"].add_message(channel, message, sender)
    
    # Play chat sound based on channel
    sound_name = "ui_chat_message"
    if channel == "Whisper":
        sound_name = "ui_chat_whisper"
    elif channel == "Party" or channel == "Raid":
        sound_name = "ui_chat_party"
    elif channel == "Guild":
        sound_name = "ui_chat_guild"
    
    self.audio_manager.play_sound(sound_name)

def update_party_frames(self, event_data: Dict):
    """Handle party updated event.
    
    Args:
        event_data: Event data containing party information
    """
    if "party_frame" not in self.elements:
        return
    
    party_data = self.player_manager.get_party_data()
    if party_data:
        self.elements["party_frame"].update_party(party_data)
    else:
        self.elements["party_frame"].clear()

def start_ability_cooldown(self, event_data: Dict):
    """Handle ability cooldown start event.
    
    Args:
        event_data: Event data containing cooldown information
    """
    ability_id = event_data.get("ability_id")
    duration = event_data.get("duration", 0)
    
    if not ability_id or duration <= 0:
        return
    
    # Update all action bars that might contain this ability
    for bar_id in ["main_action_bar", "secondary_action_bar", "side_action_bar"]:
        if bar_id in self.elements:
            self.elements[bar_id].start_cooldown(ability_id, duration)

def end_ability_cooldown(self, event_data: Dict):
    """Handle ability cooldown end event.
    
    Args:
        event_data: Event data containing cooldown information
    """
    ability_id = event_data.get("ability_id")
    
    if not ability_id:
        return
    
    # Update all action bars that might contain this ability
    for bar_id in ["main_action_bar", "secondary_action_bar", "side_action_bar"]:
        if bar_id in self.elements:
            self.elements[bar_id].end_cooldown(ability_id)
    
    # Play cooldown end sound
    self.audio_manager.play_sound("ui_ability_ready")

def update_minimap(self, event_data: Dict):
    """Handle minimap updated event.
    
    Args:
        event_data: Event data containing minimap information
    """
    if "minimap" not in self.elements:
        return
    
    # Update player position on minimap
    if "player_pos" in event_data:
        self.elements["minimap"].set_player_position(event_data["player_pos"])
    
    # Update minimap markers
    if "markers" in event_data:
        self.elements["minimap"].update_markers(event_data["markers"])
    
    # Update tracked quests on minimap
    if "quest_markers" in event_data:
        self.elements["minimap"].update_quest_markers(event_data["quest_markers"])

def on_update(self, delta_time: float):
    """Update HUD elements.
    
    Args:
        delta_time: Time elapsed since last update in seconds
    """
    if not self.is_visible:
        return
    
    # Update all elements
    for element in self.elements.values():
        if element.is_visible():
            element.on_update(delta_time)
    
    # Update tooltip if hovering over an element
    if self.hover_element is not None:
        tooltip_data = self.hover_element.get_tooltip_data()
        if tooltip_data:
            self.tooltip_manager.show(tooltip_data)
        else:
            self.tooltip_manager.hide()
    else:
        self.tooltip_manager.hide()

def on_render(self, renderer):
    """Render HUD elements.
    
    Args:
        renderer: Renderer interface for drawing
    """
    if not self.is_visible:
        return
    
    # Render all visible elements
    for element in self.elements.values():
        if element.is_visible():
            element.on_render(renderer)
    
    # Render tooltip if shown
    self.tooltip_manager.on_render(renderer)

def on_mouse_move(self, x: int, y: int):
    """Handle mouse movement events.
    
    Args:
        x: Mouse x coordinate
        y: Mouse y coordinate
    """
    if not self.is_visible:
        return False
    
    # Check if mouse is over any element
    self.hover_element = None
    for element in reversed(list(self.elements.values())):  # Check top elements first
        if element.is_visible() and element.contains_point(x, y):
            if element.on_mouse_move(x, y):
                self.hover_element = element
                return True
    
    return False

def on_mouse_press(self, x: int, y: int, button: int):
    """Handle mouse press events.
    
    Args:
        x: Mouse x coordinate
        y: Mouse y coordinate
        button: Mouse button pressed
    """
    if not self.is_visible:
        return False
    
    # Check if any element was clicked
    for element in reversed(list(self.elements.values())):  # Check top elements first
        if element.is_visible() and element.contains_point(x, y):
            if element.on_mouse_press(x, y, button):
                return True
    
    return False

def on_mouse_release(self, x: int, y: int, button: int):
    """Handle mouse release events.
    
    Args:
        x: Mouse x coordinate
        y: Mouse y coordinate
        button: Mouse button released
    """
    if not self.is_visible:
        return False
    
    # Check if any element was released
    for element in reversed(list(self.elements.values())):  # Check top elements first
        if element.is_visible() and element.contains_point(x, y):
            if element.on_mouse_release(x, y, button):
                return True
    
    return False

def on_key_press(self, key: int, modifiers: int):
    """Handle key press events.
    
    Args:
        key: Key code pressed
        modifiers: Modifier keys active
    """
    if not self.is_visible:
        return False
    
    # Pass key press to chat box if it's active
    if "chat_box" in self.elements and self.elements["chat_box"].is_input_active():
        return self.elements["chat_box"].on_key_press(key, modifiers)
    
    # Check for hotkey bindings
    action = self.player_manager.get_keybinding(key, modifiers)
    if action:
        if action.startswith("ability_"):
            ability_id = action[8:]  # Remove "ability_" prefix
            self.event_manager.trigger("ability_activated", {"ability_id": ability_id})
            return True
        elif action == "toggle_inventory":
            self.event_manager.trigger("toggle_inventory", {})
            return True
        elif action == "toggle_character":
            self.event_manager.trigger("toggle_character", {})
            return True
        elif action == "toggle_quest_log":
            self.event_manager.trigger("toggle_quest_log", {})
            return True
        elif action == "toggle_map":
            self.event_manager.trigger("toggle_map", {})
            return True
        elif action == "toggle_chat":
            if "chat_box" in self.elements:
                self.elements["chat_box"].toggle_input()
            return True
    
    return False

def on_text_input(self, text: str):
    """Handle text input events.
    
    Args:
        text: Text input
    """
    if not self.is_visible:
        return False
    
    # Pass text input to chat box if it's active
    if "chat_box" in self.elements and self.elements["chat_box"].is_input_active():
        return self.elements["chat_box"].on_text_input(text)
    
    return False

def cleanup(self):
    """Clean up resources and event listeners."""
    # Remove event listeners
    self.event_manager.remove_listener("show_hud", self.show)
    self.event_manager.remove_listener("hide_hud", self.hide)
    self.event_manager.remove_listener("enter_combat", self.enter_combat)
    self.event_manager.remove_listener("exit_combat", self.exit_combat)
    self.event_manager.remove_listener("enter_safe_zone", self.enter_safe_zone)
    self.event_manager.remove_listener("exit_safe_zone", self.exit_safe_zone)
    self.event_manager.remove_listener("player_health_changed", self.update_player_health)
    self.event_manager.remove_listener("player_mana_changed", self.update_player_mana)
    self.event_manager.remove_listener("player_exp_changed", self.update_player_experience)
    self.event_manager.remove_listener("quest_updated", self.update_quest_tracker)
    self.event_manager.remove_listener("inventory_updated", self.update_inventory)
    self.event_manager.remove_listener("target_changed", self.update_target)
    self.event_manager.remove_listener("buff_applied", self.add_buff)
    self.event_manager.remove_listener("buff_removed", self.remove_buff)
    self.event_manager.remove_listener("chat_message_received", self.add_chat_message)
    self.event_manager.remove_listener("party_updated", self.update_party_frames)
    self.event_manager.remove_listener("ability_cooldown_start", self.start_ability_cooldown)
    self.event_manager.remove_listener("ability_cooldown_end", self.end_ability_cooldown)
    self.event_manager.remove_listener("minimap_updated", self.update_minimap)
    
    # Clean up elements
    for element in self.elements.values():
        element.cleanup()
    
    self.elements.clear()
    self.logger.info("MMORPG HUD resources cleaned up")