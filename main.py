#!/usr/bin/env python3
"""
MultiGenre Game System - Main Entry Point
This script initializes and runs the game, handling core functionality and game mode selection.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Core system imports
from core.modules.gameLoop import GameLoop
from core.modules.eventManager import EventManager
from core.modules.timeManager import TimeManager
from core.modules.aiManager import AIManager
from core.modules.resourceManager import ResourceManager

# Game mode imports
from fps.system.gunSystem import GunSystem
from fps.system.fpsUI import FPSUI
from fps.system.fpsModes import FpsMode
from fps.system.aimAssist import AimAssist
from fps.system.lootSystem  import LootSystem
from fps.system.damageHandler import DamageHandler
from moba.logic.heroSystem import HeroSystem
from moba.logic.mobaUI import MobaUI
from moba.logic.minionAI import MinionAi
from moba.logic.mobaMap import Mobamap
from moba.logic.mobaModes import MobaModes
from moba.logic.roleManager import RoleManager
from mmorpg.mechanics.questSystem import QuestSystem
from mmorpg.mechanics.worldMap import WorldMap
from mmorpg.mechanics.classSystem import ClassSystem
from mmorpg.mechanics.mountSystem import MountSystem
from mmorpg.mechanics.questSystem import QuestSystem
from mmorpg.mechanics.skillTree import SkillTree

# Networking imports
from networking.engine.websocketHandler import WebsocketHandler
from networking.engine.serverSync import ServerSync
from networking.engine.antiCheat import AntiCheat
from networking.engine.chatSystem import ChatSystem
from networking.engine.dataEncryption import DataEncryption

# UI imports
from ui.interface.mainMenu import MainMenu
from ui.interface.pauseMenu import PauseMenu
from ui.interface.fpsHUD import FpsHUD
from ui.interface.loadingScreens import LoadingScreens
from ui.interface.mmorpgHUD import MmorpgHUD
from ui.interface.shopInterface import ShopInterface
from ui.interface.mobaHUD import MobaHUD

# Multiplayer imports
from multiplayer.network.sessionManager import SessionManager
from multiplayer.network.lobbySystem import LobbySystem
from multiplayer.network.friendSystem import FriendSystem
from multiplayer.network.guildSystem import GuildSystem
from multiplayer.network.partySystem import PartySystem

# Script imports
from scripts.logic.cameraController import CameraController
from scripts.logic.inputManager import InputManager
from scripts.logic.analytics import Analytics
from scripts.effects.explosionEffect import ExplosionEffect
from scripts.effects.healEffect import HealEffect
from scripts.effects.strikeEffect import StrikeEffect
from scripts.logic.botLogic import BotLogic
from scripts.logic.replaySystem import ReplaySystem


class GameEngine:
    """Main game engine class that coordinates all game systems and modes."""
    
    def __init__(self, config_path='configs/data/serverSettings.json'):
        """Initialize the game engine with configuration."""
        self.logger = self._setup_logging()
        self.logger.info("Initializing game engine...")
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize core systems
        self.event_manager = EventManager()
        self.time_manager = TimeManager()
        self.resource_manager = ResourceManager()
        self.ai_manager = AIManager()
        self.ai_game_loop =GameLoop()
        
        # Initialize networking
        self.websocket_handler = WebsocketHandler()
        self.server_sync = ServerSync()
        self.anti_cheat = AntiCheat()
        self.chat_system = ChatSystem()
        self.data_encrytion =DataEncryption()
        
        # Initialize session management
        self.session_manager = SessionManager()
        self.lobby_system = LobbySystem()
        self.friend_system = FriendSystem()
        self.guild_system = GuildSystem()
        self.party_system = PartySystem()
        
        
        # Initialize user interface
        self.main_menu = MainMenu()
        self.pause_menu = PauseMenu()
        self.loading_screens = LoadingScreens()
        self.mmorpg_hud = MmorpgHUD()
        self.moba_hud = MobaHUD()
        self.shop_interface = ShopInterface()
        self.fps_hud = FpsHUD()
        
        
        # Initialize player systems
        self.camera_controller = CameraController()
        self.input_manager = InputManager()
        self.analytics = Analytics()
        self.bot_logic = BotLogic()
        self.replay_system =ReplaySystem     
        self.explosion_effects = ExplosionEffect
        
        
        # Game mode handlers - will be initialized on demand
        self.current_game_mode = None
        self.fps_mode = None
        self.moba_mode = None
        self.mmorpg_mode = None
        
        # Game state
        self.is_running = False
        self.current_scene = "main_menu"
        
        self.logger.info("Game engine initialized successfully")
    
    def _setup_logging(self):
        """Set up logging system."""
        logger = logging.getLogger('GameEngine')
        logger.setLevel(logging.INFO)
        
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Create file handler
        os.makedirs('backend/serverLogs', exist_ok=True)
        file_handler = logging.FileHandler('backend/serverLogs/game.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_config(self, config_path):
        """Load game configuration from JSON file."""
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
                self.logger.info(f"Configuration loaded from {config_path}")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def _initialize_game_mode(self, mode):
        """Initialize the selected game mode."""
        self.logger.info(f"Initializing game mode: {mode}")
        
        if mode == "fps":
            from fps.system.fpsModes import FPSMode
            self.fps_mode = FPSMode()
            self.current_game_mode = self.fps_mode
        elif mode == "moba":
            from moba.logic.mobaModes import MobaMode
            self.moba_mode = MobaMode()
            self.current_game_mode = self.moba_mode
        elif mode == "mmorpg":
            from mmorpg.mechanics.classSystem import ClassSystem
            self.mmorpg_mode = ClassSystem()
            self.current_game_mode = self.mmorpg_mode
        else:
            self.logger.error(f"Unknown game mode: {mode}")
            return False
        
        return True
    
    def start(self):
        """Start the game engine."""
        self.logger.info("Starting game engine")
        self.is_running = True
        
        # Show main menu
        self.main_menu.show()
        
        # Create game loop
        self.game_loop = GameLoop(self.event_manager, self.time_manager)
        
        try:
            # Start the game loop
            self.game_loop.start(self)
        except Exception as e:
            self.logger.error(f"Game crashed: {e}")
        finally:
            self.shutdown()
    
    def change_scene(self, scene_name, **params):
        """Change the current scene."""
        self.logger.info(f"Changing scene to: {scene_name}")
        
        # Clean up current scene if needed
        if self.current_scene == "gameplay" and scene_name != "gameplay":
            self.current_game_mode = None
        
        self.current_scene = scene_name
        
        if scene_name == "main_menu":
            self.main_menu.show()
        elif scene_name == "gameplay":
            game_mode = params.get("mode", "fps")
            success = self._initialize_game_mode(game_mode)
            if not success:
                self.change_scene("main_menu")
        elif scene_name == "pause":
            self.pause_menu.show()
        else:
            self.logger.warning(f"Unknown scene: {scene_name}")
    
    def process_input(self, input_event):
        """Process user input."""
        # Delegate input processing to current scene
        if self.current_scene == "main_menu":
            self.main_menu.process_input(input_event)
        elif self.current_scene == "gameplay" and self.current_game_mode:
            self.current_game_mode.process_input(input_event)
        elif self.current_scene == "pause":
            self.pause_menu.process_input(input_event)
    
    def update(self, delta_time):
        """Update game state."""
        # Update systems
        self.time_manager.update(delta_time)
        
        # Update current scene
        if self.current_scene == "gameplay" and self.current_game_mode:
            self.current_game_mode.update(delta_time)
            self.camera_controller.update(delta_time)
        
        # Update networking
        if self.websocket_handler.is_connected():
            self.server_sync.update(delta_time)
            self.anti_cheat.scan()
    
    def render(self):
        """Render the current frame."""
        if self.current_scene == "main_menu":
            self.main_menu.render()
        elif self.current_scene == "gameplay" and self.current_game_mode:
            self.current_game_mode.render()
        elif self.current_scene == "pause":
            self.pause_menu.render()
    
    def shutdown(self):
        """Shutdown the game engine."""
        self.logger.info("Shutting down game engine")
        self.is_running = False
        
        # Clean up resources
        self.resource_manager.cleanup()
        
        # Close network connections
        if self.websocket_handler.is_connected():
            self.websocket_handler.disconnect()
        
        self.logger.info("Game engine shutdown complete")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='MultiGenre Game System')
    parser.add_argument('--mode', type=str, default=None, choices=['fps', 'moba', 'mmorpg'],
                        help='Start directly in the specified game mode')
    parser.add_argument('--dev', action='store_true', help='Enable developer mode')
    parser.add_argument('--config', type=str, default='configs/data/serverSettings.json',
                        help='Path to configuration file')
    return parser.parse_args()


def main():
    """Main entry point for the game."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize game engine
    engine = GameEngine(config_path=args.config)
    
    # Start in specific mode if requested
    if args.mode:
        engine.change_scene("gameplay", mode=args.mode)
    
    # Enable developer mode if requested
    if args.dev:
        logging.getLogger().setLevel(logging.DEBUG)
        print("Developer mode enabled")
    
    # Start the game
    engine.start()


if __name__ == "__main__":
    main()