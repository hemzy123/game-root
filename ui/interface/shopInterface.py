#!/usr/bin/env python3
"""
Shop Interface Module - Handles in-game shops for all game modes
This module provides shop functionality for FPS, MOBA, and MMORPG game modes,
including item purchasing, selling, and currency management.
"""

import json
import logging
import os
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# Core system imports
from core.modules.eventManager import EventManager
from core.modules.resourceManager import ResourceManager

# Network imports
from networking.engine.serverSync import ServerSync
from backend.purchases.transactionManager import TransactionManager

# UI imports
from ui.interface.uiElement import UIElement
from ui.interface.uiTheme import UITheme


class ShopType(Enum):
    """Enumeration of different shop types available in the game."""
    FPS_WEAPON = 1
    FPS_EQUIPMENT = 2
    MOBA_ITEM = 3
    MOBA_CONSUMABLE = 4
    MMORPG_GEAR = 5
    MMORPG_CONSUMABLE = 6
    MMORPG_CRAFTING = 7
    PREMIUM = 8


class ShopCategory:
    """Represents a category of items in a shop."""
    
    def __init__(self, category_id: str, name: str, icon_path: str):
        """Initialize a shop category.
        
        Args:
            category_id: Unique identifier for the category
            name: Display name for the category
            icon_path: Path to category icon
        """
        self.id = category_id
        self.name = name
        self.icon_path = icon_path
        self.items = []
    
    def add_item(self, item):
        """Add an item to this category."""
        self.items.append(item)
    
    def to_dict(self):
        """Convert category to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon_path,
            "items": [item.to_dict() for item in self.items]
        }


class ShopItem:
    """Represents an item available for purchase in a shop."""
    
    def __init__(self, item_id: str, name: str, description: str, price: int, 
                 icon_path: str, category_id: str, game_mode: str,
                 level_req: int = 0, premium: bool = False):
        """Initialize a shop item.
        
        Args:
            item_id: Unique identifier for the item
            name: Display name for the item
            description: Item description
            price: Item price in relevant currency
            icon_path: Path to item icon
            category_id: ID of the category this item belongs to
            game_mode: Game mode this item is for (fps, moba, mmorpg, all)
            level_req: Level requirement for buying this item
            premium: Whether this item is a premium item
        """
        self.id = item_id
        self.name = name
        self.description = description
        self.price = price
        self.icon_path = icon_path
        self.category_id = category_id
        self.game_mode = game_mode
        self.level_req = level_req
        self.premium = premium
        self.discount = 0
        self.stats = {}
        self.tags = []
    
    def set_stats(self, stats: Dict[str, Union[int, float, str]]):
        """Set the stats for this item.
        
        Args:
            stats: Dictionary of stat names to values
        """
        self.stats = stats
    
    def add_tag(self, tag: str):
        """Add a tag to this item.
        
        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
    
    def get_final_price(self) -> int:
        """Calculate the final price after applying discounts.
        
        Returns:
            Final price after discount
        """
        if self.discount > 0:
            return int(self.price * (1 - self.discount / 100))
        return self.price
    
    def to_dict(self):
        """Convert item to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "final_price": self.get_final_price(),
            "discount": self.discount,
            "icon": self.icon_path,
            "category": self.category_id,
            "game_mode": self.game_mode,
            "level_req": self.level_req,
            "premium": self.premium,
            "stats": self.stats,
            "tags": self.tags
        }


class PlayerInventory:
    """Manages the player's inventory and currencies."""
    
    def __init__(self, player_id: str):
        """Initialize player inventory.
        
        Args:
            player_id: ID of the player this inventory belongs to
        """
        self.player_id = player_id
        self.items = {}  # Dict of item_id to quantity
        self.currencies = {
            "gold": 0,
            "credits": 0,
            "premium_currency": 0
        }
        self.transaction_history = []
        self.logger = logging.getLogger('PlayerInventory')
    
    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        """Add an item to the inventory.
        
        Args:
            item_id: ID of the item to add
            quantity: Quantity to add
            
        Returns:
            True if successful, False otherwise
        """
        if item_id in self.items:
            self.items[item_id] += quantity
        else:
            self.items[item_id] = quantity
        
        self.logger.info(f"Added {quantity} x {item_id} to player {self.player_id}'s inventory")
        return True
    
    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """Remove an item from the inventory.
        
        Args:
            item_id: ID of the item to remove
            quantity: Quantity to remove
            
        Returns:
            True if successful, False otherwise
        """
        if item_id not in self.items or self.items[item_id] < quantity:
            self.logger.warning(f"Failed to remove {quantity} x {item_id} from player {self.player_id}'s inventory")
            return False
        
        self.items[item_id] -= quantity
        if self.items[item_id] <= 0:
            del self.items[item_id]
        
        self.logger.info(f"Removed {quantity} x {item_id} from player {self.player_id}'s inventory")
        return True
    
    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Check if the inventory has the specified item.
        
        Args:
            item_id: ID of the item to check
            quantity: Quantity to check
            
        Returns:
            True if the inventory has enough of the item, False otherwise
        """
        return item_id in self.items and self.items[item_id] >= quantity
    
    def add_currency(self, currency_type: str, amount: int) -> bool:
        """Add currency to the inventory.
        
        Args:
            currency_type: Type of currency to add
            amount: Amount to add
            
        Returns:
            True if successful, False otherwise
        """
        if currency_type not in self.currencies:
            self.logger.warning(f"Unknown currency type: {currency_type}")
            return False
        
        self.currencies[currency_type] += amount
        self.logger.info(f"Added {amount} {currency_type} to player {self.player_id}")
        return True
    
    def remove_currency(self, currency_type: str, amount: int) -> bool:
        """Remove currency from the inventory.
        
        Args:
            currency_type: Type of currency to remove
            amount: Amount to remove
            
        Returns:
            True if successful, False otherwise
        """
        if currency_type not in self.currencies:
            self.logger.warning(f"Unknown currency type: {currency_type}")
            return False
        
        if self.currencies[currency_type] < amount:
            self.logger.warning(f"Not enough {currency_type} for player {self.player_id}")
            return False
        
        self.currencies[currency_type] -= amount
        self.logger.info(f"Removed {amount} {currency_type} from player {self.player_id}")
        return True
    
    def has_currency(self, currency_type: str, amount: int) -> bool:
        """Check if the inventory has the specified currency.
        
        Args:
            currency_type: Type of currency to check
            amount: Amount to check
            
        Returns:
            True if the inventory has enough of the currency, False otherwise
        """
        return currency_type in self.currencies and self.currencies[currency_type] >= amount
    
    def add_transaction(self, transaction_type: str, item_id: str, quantity: int, price: int, currency_type: str):
        """Add a transaction to the history.
        
        Args:
            transaction_type: Type of transaction (buy, sell)
            item_id: ID of the item involved
            quantity: Quantity involved
            price: Price per item
            currency_type: Type of currency used
        """
        transaction = {
            "type": transaction_type,
            "item_id": item_id,
            "quantity": quantity,
            "price": price,
            "currency": currency_type,
            "timestamp": self.get_timestamp()
        }
        self.transaction_history.append(transaction)
    
    def get_timestamp(self):
        """Get the current timestamp."""
        import time
        return int(time.time())
    
    def save(self):
        """Save the inventory to disk."""
        try:
            os.makedirs(f"backend/playerData/{self.player_id}", exist_ok=True)
            data = {
                "items": self.items,
                "currencies": self.currencies,
                "transactions": self.transaction_history
            }
            with open(f"backend/playerData/{self.player_id}/inventory.json", 'w') as f:
                json.dump(data, f)
            
            self.logger.info(f"Saved inventory for player {self.player_id}")
        except Exception as e:
            self.logger.error(f"Failed to save inventory for player {self.player_id}: {e}")
    
    def load(self):
        """Load the inventory from disk."""
        try:
            path = f"backend/playerData/{self.player_id}/inventory.json"
            if not os.path.exists(path):
                self.logger.info(f"No inventory found for player {self.player_id}, creating new")
                return
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.items = data.get("items", {})
            self.currencies = data.get("currencies", {"gold": 0, "credits": 0, "premium_currency": 0})
            self.transaction_history = data.get("transactions", [])
            
            self.logger.info(f"Loaded inventory for player {self.player_id}")
        except Exception as e:
            self.logger.error(f"Failed to load inventory for player {self.player_id}: {e}")


class ShopInterface(UIElement):
    """Main shop interface class that handles displaying and interacting with shops."""
    
    def __init__(self, event_manager: EventManager, resource_manager: ResourceManager, 
                 server_sync: ServerSync, transaction_manager: TransactionManager):
        """Initialize the shop interface.
        
        Args:
            event_manager: Event manager for handling shop events
            resource_manager: Resource manager for loading shop assets
            server_sync: Server sync for syncing purchases with the server
            transaction_manager: Transaction manager for handling purchases
        """
        super().__init__()
        self.event_manager = event_manager
        self.resource_manager = resource_manager
        self.server_sync = server_sync
        self.transaction_manager = transaction_manager
        self.logger = logging.getLogger('ShopInterface')
        
        # Shop data
        self.categories = {}  # Dict of category_id to ShopCategory
        self.items = {}  # Dict of item_id to ShopItem
        self.active_shop_type = None
        self.active_game_mode = None
        self.currency_types = {
            ShopType.FPS_WEAPON: "credits",
            ShopType.FPS_EQUIPMENT: "credits",
            ShopType.MOBA_ITEM: "gold",
            ShopType.MOBA_CONSUMABLE: "gold",
            ShopType.MMORPG_GEAR: "gold",
            ShopType.MMORPG_CONSUMABLE: "gold",
            ShopType.MMORPG_CRAFTING: "gold",
            ShopType.PREMIUM: "premium_currency"
        }
        
        # UI state
        self.is_visible = False
        self.selected_category_id = None
        self.selected_item_id = None
        self.player_inventory = None
        self.ui_theme = None
        
        # Register event listeners
        self.event_manager.add_listener("open_shop", self.open_shop)
        self.event_manager.add_listener("close_shop", self.close)
        self.event_manager.add_listener("purchase_item", self.purchase_item)
        self.event_manager.add_listener("sell_item", self.sell_item)
        
        # Load shop data
        self.load_shop_data()
    
    def load_shop_data(self):
        """Load shop data from configuration files."""
        try:
            # Load shop categories
            with open("configs/data/shopCategories.json", 'r') as f:
                categories_data = json.load(f)
            
            for cat_data in categories_data:
                category = ShopCategory(
                    cat_data["id"],
                    cat_data["name"],
                    cat_data["icon"]
                )
                self.categories[category.id] = category
            
            # Load shop items
            with open("configs/data/shopItems.json", 'r') as f:
                items_data = json.load(f)
            
            for item_data in items_data:
                item = ShopItem(
                    item_data["id"],
                    item_data["name"],
                    item_data["description"],
                    item_data["price"],
                    item_data["icon"],
                    item_data["category"],
                    item_data["game_mode"],
                    item_data.get("level_req", 0),
                    item_data.get("premium", False)
                )
                
                # Add stats if available
                if "stats" in item_data:
                    item.set_stats(item_data["stats"])
                
                # Add tags if available
                if "tags" in item_data:
                    for tag in item_data["tags"]:
                        item.add_tag(tag)
                
                # Add discount if available
                if "discount" in item_data:
                    item.discount = item_data["discount"]
                
                self.items[item.id] = item
                
                # Add item to its category
                if item.category_id in self.categories:
                    self.categories[item.category_id].add_item(item)
            
            # Load UI theme
            with open("configs/data/uiThemes.json", 'r') as f:
                themes_data = json.load(f)
                self.ui_theme = UITheme(themes_data.get("shop", {}))
            
            self.logger.info("Shop data loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load shop data: {e}")
    
    def open_shop(self, shop_type: ShopType, game_mode: str, player_id: str):
        """Open the shop interface.
        
        Args:
            shop_type: Type of shop to open
            game_mode: Current game mode
            player_id: ID of the player opening the shop
        """
        self.logger.info(f"Opening shop type {shop_type} for player {player_id} in {game_mode} mode")
        
        self.active_shop_type = shop_type
        self.active_game_mode = game_mode
        self.is_visible = True
        
        # Load player inventory
        self.player_inventory = PlayerInventory(player_id)
        self.player_inventory.load()
        
        # Select the first category by default
        filtered_categories = self.get_filtered_categories()
        if filtered_categories:
            self.selected_category_id = filtered_categories[0].id
        
        # Trigger shop opened event
        self.event_manager.trigger("shop_opened", {
            "shop_type": shop_type,
            "game_mode": game_mode,
            "player_id": player_id
        })
    
    def close(self):
        """Close the shop interface."""
        if not self.is_visible:
            return
        
        self.logger.info("Closing shop interface")
        
        # Save player inventory
        if self.player_inventory:
            self.player_inventory.save()
        
        self.is_visible = False
        self.active_shop_type = None
        self.selected_category_id = None
        self.selected_item_id = None
        
        # Trigger shop closed event
        self.event_manager.trigger("shop_closed", {})
    
    def get_filtered_categories(self) -> List[ShopCategory]:
        """Get categories filtered for the current shop type and game mode.
        
        Returns:
            List of categories for the current shop type and game mode
        """
        filtered = []
        for category in self.categories.values():
            # Check if category has items for this shop type and game mode
            has_items = False
            for item in category.items:
                if (self.active_game_mode in item.game_mode or item.game_mode == "all") and \
                   self.is_item_for_shop_type(item.id, self.active_shop_type):
                    has_items = True
                    break
            
            if has_items:
                filtered.append(category)
        
        return filtered
    
    def get_filtered_items(self, category_id: str) -> List[ShopItem]:
        """Get items filtered for the current shop type, game mode, and category.
        
        Args:
            category_id: ID of the category to filter items for
            
        Returns:
            List of items for the current shop type, game mode, and category
        """
        filtered = []
        
        if category_id in self.categories:
            for item in self.categories[category_id].items:
                if (self.active_game_mode in item.game_mode or item.game_mode == "all") and \
                   self.is_item_for_shop_type(item.id, self.active_shop_type):
                    filtered.append(item)
        
        return filtered
    
    def is_item_for_shop_type(self, item_id: str, shop_type: ShopType) -> bool:
        """Check if an item is for a specific shop type.
        
        Args:
            item_id: ID of the item to check
            shop_type: Shop type to check for
            
        Returns:
            True if the item is for the shop type, False otherwise
        """
        if item_id not in self.items:
            return False
        
        item = self.items[item_id]
        
        # Check based on shop type and item properties
        if shop_type == ShopType.FPS_WEAPON:
            return "weapon" in item.tags and item.game_mode in ["fps", "all"]
        elif shop_type == ShopType.FPS_EQUIPMENT:
            return "equipment" in item.tags and item.game_mode in ["fps", "all"]
        elif shop_type == ShopType.MOBA_ITEM:
            return "item" in item.tags and item.game_mode in ["moba", "all"]
        elif shop_type == ShopType.MOBA_CONSUMABLE:
            return "consumable" in item.tags and item.game_mode in ["moba", "all"]
        elif shop_type == ShopType.MMORPG_GEAR:
            return "gear" in item.tags and item.game_mode in ["mmorpg", "all"]
        elif shop_type == ShopType.MMORPG_CONSUMABLE:
            return "consumable" in item.tags and item.game_mode in ["mmorpg", "all"]
        elif shop_type == ShopType.MMORPG_CRAFTING:
            return "crafting" in item.tags and item.game_mode in ["mmorpg", "all"]
        elif shop_type == ShopType.PREMIUM:
            return item.premium
        
        return False
    
    def select_category(self, category_id: str):
        """Select a category in the shop.
        
        Args:
            category_id: ID of the category to select
        """
        if category_id in self.categories:
            self.selected_category_id = category_id
            
            # Select the first item in the category
            filtered_items = self.get_filtered_items(category_id)
            if filtered_items:
                self.selected_item_id = filtered_items[0].id
            else:
                self.selected_item_id = None
    
    def select_item(self, item_id: str):
        """Select an item in the shop.
        
        Args:
            item_id: ID of the item to select
        """
        if item_id in self.items:
            self.selected_item_id = item_id
    
    def purchase_item(self, item_id: str, quantity: int = 1) -> bool:
        """Purchase an item from the shop.
        
        Args:
            item_id: ID of the item to purchase
            quantity: Quantity to purchase
            
        Returns:
            True if purchase was successful, False otherwise
        """
        if not self.player_inventory or not self.is_visible:
            self.logger.warning("Cannot purchase item: shop not open or inventory not loaded")
            return False
        
        if item_id not in self.items:
            self.logger.warning(f"Cannot purchase item: item {item_id} not found")
            return False
        
        item = self.items[item_id]
        
        # Check if the shop sells this item
        if not self.is_item_for_shop_type(item_id, self.active_shop_type):
            self.logger.warning(f"Shop does not sell item {item_id}")
            return False
        
        # Get currency type for this shop
        currency_type = self.currency_types.get(self.active_shop_type, "gold")
        total_price = item.get_final_price() * quantity
        
        # Check if player has enough currency
        if not self.player_inventory.has_currency(currency_type, total_price):
            self.logger.info(f"Player does not have enough {currency_type} to purchase {quantity} x {item_id}")
            
            # Trigger purchase failed event
            self.event_manager.trigger("purchase_failed", {
                "reason": "not_enough_currency",
                "item_id": item_id,
                "quantity": quantity,
                "price": total_price,
                "currency": currency_type
            })
            
            return False
        
        # Process the transaction
        transaction_id = self.transaction_manager.create_transaction(
            self.player_inventory.player_id,
            "purchase",
            item_id,
            quantity,
            total_price,
            currency_type
        )
        
        # Wait for server confirmation if online
        if self.server_sync.is_connected():
            confirmed = self.server_sync.confirm_transaction(transaction_id)
            if not confirmed:
                self.logger.warning(f"Transaction {transaction_id} not confirmed by server")
                
                # Trigger purchase failed event
                self.event_manager.trigger("purchase_failed", {
                    "reason": "server_rejected",
                    "item_id": item_id,
                    "quantity": quantity,
                    "price": total_price,
                    "currency": currency_type
                })
                
                return False
        
        # Update player inventory
        self.player_inventory.remove_currency(currency_type, total_price)
        self.player_inventory.add_item(item_id, quantity)
        self.player_inventory.add_transaction("buy", item_id, quantity, item.get_final_price(), currency_type)
        
        # Trigger purchase successful event
        self.event_manager.trigger("purchase_successful", {
            "transaction_id": transaction_id,
            "item_id": item_id,
            "quantity": quantity,
            "price": total_price,
            "currency": currency_type
        })
        
        self.logger.info(f"Player purchased {quantity} x {item_id} for {total_price} {currency_type}")
        return True
    
    def sell_item(self, item_id: str, quantity: int = 1) -> bool:
        """Sell an item to the shop.
        
        Args:
            item_id: ID of the item to sell
            quantity: Quantity to sell
            
        Returns:
            True if sale was successful, False otherwise
        """
        if not self.player_inventory or not self.is_visible:
            self.logger.warning("Cannot sell item: shop not open or inventory not loaded")
            return False
        
        if item_id not in self.items:
            self.logger.warning(f"Cannot sell item: item {item_id} not found")
            return False
        
        # Check if player has the item
        if not self.player_inventory.has_item(item_id, quantity):
            self.logger.info(f"Player does not have {quantity} x {item_id} to sell")
            
            # Trigger sell failed event
            self.event_manager.trigger("sell_failed", {
                "reason": "not_enough_items",
                "item_id": item_id,
                "quantity": quantity
            })
            
            return False
        
        # Get item and calculate sell price (usually a percentage of buy price)
        item = self.items[item_id]
        sell_price = int(item.get_final_price() * 0.5)  # 50% of buy price
        total_sell_price = sell_price * quantity
        
        # Get currency type for this shop
        currency_type = self.currency_types.get(self.active_shop_type, "gold")
        
        # Process the transaction
        transaction_id = self.transaction_manager.create_transaction(
            self.player_inventory.player_id,
            "sell",
            item_id,
            quantity,
            total_sell_price,
            currency_type
        )
        
        # Wait for server confirmation if online
        if self.server_sync.is_connected():
            confirmed = self.server_sync.confirm_transaction(transaction_id)
            if not confirmed:
                self.logger.warning(f"Transaction {transaction_id} not confirmed by server")
                
                # Trigger sell failed event
                self.event_manager.trigger("sell_failed", {
                    "reason": "server_rejected",
                    "item_id": item_id,
                    "quantity": quantity,
                    "price": total_sell_price,
                    "currency": currency_type
                })
                
                return False
        
        # Update player inventory
        self.player_inventory.remove_item(item_id, quantity)
        self.player_inventory.add_currency(currency_type, total_sell_price)
        self.player_inventory.add_transaction("sell", item_id, quantity, sell_price, currency_type)
        
        # Trigger sell successful event
        self.event_manager.trigger("sell_successful", {
            "transaction_id": transaction_id,
            "item_id": item_id,
            "quantity": quantity,
            "price": total_sell_price,
            "currency": currency_type
        })
        
        self.logger.info(f"Player sold {quantity} x {item_id} for {total_sell_price} {currency_type}")
        return True
    
    def get_item_details(self, item_id: str) -> Optional[Dict]:
        """Get details for an item.
        
        Args:
            item_id: ID of the item to get details for
            
        Returns:
            Dictionary of item details, or None if item not found
        """
        if item_id in self.items:
            item = self.items[item_id]
            return item.to_dict()
        return None
    
    def get_player_currency(self, currency_type: str) -> int:
        """Get the amount of currency the player has.
        
        Args:
            currency_type: Type of currency to check
            
        Returns:
            Amount of currency the player has
        """
        if self.player_inventory:
            return self.player_inventory.currencies.get(currency_type, 0)
        return 0
    
    def update(self, delta_time: float):
        """Update the shop interface.
        
        Args:
            delta_time: Time since last update
        """
        if not self.is_visible:
            return
        
        # Apply any pending discounts or price changes
        self._update_discounts()
    
    def _update_discounts(self):
        """Update discounts for items in the shop."""
        # This could be updated from server data, time-based sales, etc.
        pass
    
    def render(self):
        """Render the shop interface."""
        if not self.is_visible:
            return
        
        # The actual rendering would depend on the game's UI system
        # This is just a placeholder for the logic
        
        # Render categories
        self._render_categories()
        
        # Render items
        if self.selected_category_id:
            self._render_items()
        
        # Render selected item details
        if self.selected_item_id:
            self._render_item_details()
        
        # Render player info (currency, etc.)
        self._render_player_info()
    
    def _render_categories(self):
        """Render the shop categories."""
        # This would be implemented by the game's UI system
        pass
    
    def _render_items(self):
        """Render the items in the selected category."""
        # This would be implemented by the game's UI system
        pass
    
    def _render_item_details(self):
        """Render the details of the selected item."""
        # This would be implemented by the game's UI system
        pass
    
    def _render_player_info(self):
        """Render the player's currency and other info."""
        # This would be implemented by the game's UI system
        pass
    
    def process_input(self, input_event):
        """Process input events for the shop interface.
        
        Args:
            input_event: Input event to process
        """
        if not self.is_visible:
            return
        
        # Handle navigation between categories and items
        if input_event.type == "key_press":
            if input_event.key == "escape":
                self.close()
            elif input_event.key == "tab":
                self._cycle_categories()
            # Add more input handling as needed
        
        # Handle mouse
        elif input_event.type == "mouse_click":
            # Check if click is on a category
            clicked_category = self._get_category_at_position(input_event.position)
            if clicked_category:
                self.select_category(clicked_category.id)
                return
            
            # Check if click is on an item
            clicked_item = self._get_item_at_position(input_event.position)
            if clicked_item:
                self.select_item(clicked_item.id)
                return
            
            # Check if click is on buy button
            if self._is_position_over_buy_button(input_event.position) and self.selected_item_id:
                self.purchase_item(self.selected_item_id)
                return
            
            # Check if click is on sell button
            if self._is_position_over_sell_button(input_event.position) and self.selected_item_id:
                self.sell_item(self.selected_item_id)
                return
    
    def _cycle_categories(self, forward: bool = True):
        """Cycle through available categories.
        
        Args:
            forward: Direction to cycle (True = forward, False = backward)
        """
        filtered_categories = self.get_filtered_categories()
        if not filtered_categories:
            return
        
        # Find current category index
        current_index = -1
        for i, category in enumerate(filtered_categories):
            if category.id == self.selected_category_id:
                current_index = i
                break
        
        # If no category is selected, select the first one
        if current_index == -1:
            self.select_category(filtered_categories[0].id)
            return
        
        # Move to next/previous category
        if forward:
            next_index = (current_index + 1) % len(filtered_categories)
        else:
            next_index = (current_index - 1) % len(filtered_categories)
        
        self.select_category(filtered_categories[next_index].id)
    
    def _get_category_at_position(self, position: Tuple[int, int]) -> Optional[ShopCategory]:
        """Get the category at a specific position.
        
        Args:
            position: (x, y) position to check
            
        Returns:
            ShopCategory at position, or None if no category at position
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        # based on how categories are rendered and positioned
        return None
    
    def _get_item_at_position(self, position: Tuple[int, int]) -> Optional[ShopItem]:
        """Get the item at a specific position.
        
        Args:
            position: (x, y) position to check
            
        Returns:
            ShopItem at position, or None if no item at position
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        # based on how items are rendered and positioned
        return None
    
    def _is_position_over_buy_button(self, position: Tuple[int, int]) -> bool:
        """Check if a position is over the buy button.
        
        Args:
            position: (x, y) position to check
            
        Returns:
            True if position is over buy button, False otherwise
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        return False
    
    def _is_position_over_sell_button(self, position: Tuple[int, int]) -> bool:
        """Check if a position is over the sell button.
        
        Args:
            position: (x, y) position to check
            
        Returns:
            True if position is over sell button, False otherwise
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        return False
    
    def filter_items_by_search(self, search_text: str) -> List[ShopItem]:
        """Filter items by search text.
        
        Args:
            search_text: Text to search for
            
        Returns:
            List of items matching the search text
        """
        results = []
        
        if not search_text:
            return results
        
        search_text = search_text.lower()
        
        for item in self.items.values():
            # Skip items not for current shop type or game mode
            if not self.is_item_for_shop_type(item.id, self.active_shop_type) or \
               (self.active_game_mode not in item.game_mode and item.game_mode != "all"):
                continue
            
            # Check if item matches search
            if search_text in item.name.lower() or search_text in item.description.lower():
                results.append(item)
                continue
            
            # Check tags
            for tag in item.tags:
                if search_text in tag.lower():
                    results.append(item)
                    break
        
        return results
    
    def sort_items(self, items: List[ShopItem], sort_by: str = "name", ascending: bool = True) -> List[ShopItem]:
        """Sort a list of items.
        
        Args:
            items: List of items to sort
            sort_by: Property to sort by (name, price, level_req)
            ascending: Whether to sort in ascending order
            
        Returns:
            Sorted list of items
        """
        if sort_by == "name":
            return sorted(items, key=lambda item: item.name, reverse=not ascending)
        elif sort_by == "price":
            return sorted(items, key=lambda item: item.get_final_price(), reverse=not ascending)
        elif sort_by == "level_req":
            return sorted(items, key=lambda item: item.level_req, reverse=not ascending)
        else:
            return items
    
    def apply_discount_to_category(self, category_id: str, discount_percent: int):
        """Apply a discount to all items in a category.
        
        Args:
            category_id: ID of the category to apply discount to
            discount_percent: Discount percentage
        """
        if category_id in self.categories:
            for item in self.categories[category_id].items:
                item.discount = discount_percent
            
            self.logger.info(f"Applied {discount_percent}% discount to category {category_id}")
    
    def get_recommended_items(self, player_id: str, limit: int = 5) -> List[ShopItem]:
        """Get recommended items for a player.
        
        Args:
            player_id: ID of the player to get recommendations for
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended items
        """
        # This would typically involve more complex logic based on player preferences,
        # past purchases, and possibly ML recommendations
        # This is a simple placeholder implementation
        
        filtered_items = []
        for item in self.items.values():
            if self.is_item_for_shop_type(item.id, self.active_shop_type) and \
               (self.active_game_mode in item.game_mode or item.game_mode == "all"):
                filtered_items.append(item)
        
        # Sort by popularity, discount amount, or other criteria
        # Here we just sort randomly as an example
        import random
        random.shuffle(filtered_items)
        
        return filtered_items[:limit]
    
    def _is_tap(self, touch_end_event) -> bool:
        """Determine if a touch sequence was a tap.
        
        Args:
            touch_end_event: Touch end event to check
            
        Returns:
            True if the touch sequence was a tap, False otherwise
        """
        if not hasattr(self, '_touch_start_position') or not hasattr(self, '_touch_start_time'):
            return False
        
        # Check if touch ended quickly (less than 300ms)
        duration = self._get_current_time() - self._touch_start_time
        if duration > 0.3:  # 300ms
            return False
        
        # Check if touch didn't move much
        start_x, start_y = self._touch_start_position
        end_x, end_y = touch_end_event.position
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        
        return distance < 20  # 20 pixels threshold
    
    def _is_swipe(self, touch_end_event) -> bool:
        """Determine if a touch sequence was a swipe.
        
        Args:
            touch_end_event: Touch end event to check
            
        Returns:
            True if the touch sequence was a swipe, False otherwise
        """
        if not hasattr(self, '_touch_start_position') or not hasattr(self, '_touch_start_time'):
            return False
        
        # Check if touch ended quickly enough to be a swipe (less than 500ms)
        duration = self._get_current_time() - self._touch_start_time
        if duration > 0.5:  # 500ms
            return False
        
        # Check if touch moved enough to be a swipe
        start_x, start_y = self._touch_start_position
        end_x, end_y = touch_end_event.position
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        
        return distance > 50  # 50 pixels threshold
    
    def _handle_tap(self, position: Tuple[int, int]):
        """Handle a tap gesture.
        
        Args:
            position: (x, y) position of the tap
        """
        # Check if tap is on a category
        tapped_category = self._get_category_at_position(position)
        if tapped_category:
            self.select_category(tapped_category.id)
            return
        
        # Check if tap is on an item
        tapped_item = self._get_item_at_position(position)
        if tapped_item:
            self.select_item(tapped_item.id)
            return
        
        # Check if tap is on buy button
        if self._is_position_over_buy_button(position) and self.selected_item_id:
            self.purchase_item(self.selected_item_id)
            return
        
        # Check if tap is on sell button
        if self._is_position_over_sell_button(position) and self.selected_item_id:
            self.sell_item(self.selected_item_id)
            return
        
        # Check if tap is on back button
        if self._is_position_over_back_button(position):
            self.close()
            return
    
    def _handle_swipe(self, start_position: Tuple[int, int], end_position: Tuple[int, int]):
        """Handle a swipe gesture.
        
        Args:
            start_position: (x, y) position where the swipe started
            end_position: (x, y) position where the swipe ended
        """
        # Determine swipe direction
        start_x, start_y = start_position
        end_x, end_y = end_position
        
        # Check horizontal swipe - prioritize if both horizontal and vertical movement
        dx = end_x - start_x
        dy = end_y - start_y
        
        if abs(dx) > abs(dy):
            # Horizontal swipe
            if dx > 0:
                # Right swipe - next category
                self._cycle_categories(forward=True)
            else:
                # Left swipe - previous category
                self._cycle_categories(forward=False)
        else:
            # Vertical swipe - scroll item list
            scroll_amount = dy * -1  # Negative because down swipe should scroll down
            self._scroll_item_list(scroll_amount)
    
    def _handle_touch_drag(self, start_position: Tuple[int, int], current_position: Tuple[int, int]):
        """Handle a touch drag gesture (for scrolling).
        
        Args:
            start_position: (x, y) position where the drag started
            current_position: (x, y) current position of the drag
        """
        # For smooth scrolling during a drag
        _, start_y = start_position
        _, current_y = current_position
        
        # Calculate scrolling delta
        scroll_delta = (current_y - start_y) * -0.5  # Scale factor for smooth scrolling
        
        # Apply scrolling to items list
        self._apply_item_list_scroll(scroll_delta)
        
        # Update start position for next drag event
        self._touch_start_position = current_position
    
    def _handle_pinch_zoom(self, scale_factor: float):
        """Handle pinch zoom gesture for item details.
        
        Args:
            scale_factor: Scale factor from the pinch gesture
        """
        if self.selected_item_id and scale_factor != 1.0:
            # Apply zoom to item details view
            self._zoom_item_details(scale_factor)
    
    def _is_position_over_back_button(self, position: Tuple[int, int]) -> bool:
        """Check if a position is over the back button.
        
        Args:
            position: (x, y) position to check
            
        Returns:
            True if position is over back button, False otherwise
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        return False
    
    def _scroll_item_list(self, scroll_amount: float):
        """Scroll the item list by the specified amount.
        
        Args:
            scroll_amount: Amount to scroll (positive = down, negative = up)
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        self.logger.debug(f"Scrolling item list by {scroll_amount}")
    
    def _apply_item_list_scroll(self, scroll_delta: float):
        """Apply scrolling to the item list.
        
        Args:
            scroll_delta: Delta to scroll by
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        self.logger.debug(f"Applying item list scroll delta: {scroll_delta}")
    
    def _zoom_item_details(self, scale_factor: float):
        """Zoom item details view.
        
        Args:
            scale_factor: Scale factor to apply
        """
        # This would be implemented based on the game's UI system
        # This is a placeholder that would need actual implementation
        self.logger.debug(f"Zooming item details by factor: {scale_factor}")
    
    def _get_current_time(self) -> float:
        """Get the current time in seconds.
        
        Returns:
            Current time in seconds
        """
        import time
        return time.time()
    
    def export_shop_data(self) -> Dict:
        """Export shop data for saving or network transmission.
        
        Returns:
            Dictionary of shop data
        """
        return {
            "categories": [category.to_dict() for category in self.categories.values()],
            "items": [item.to_dict() for item in self.items.values()]
        }
    
    def import_shop_data(self, data: Dict):
        """Import shop data from saved or network data.
        
        Args:
            data: Dictionary of shop data
        """
        # Clear existing data
        self.categories = {}
        self.items = {}
        
        # Import categories
        if "categories" in data:
            for cat_data in data["categories"]:
                category = ShopCategory(
                    cat_data["id"],
                    cat_data["name"],
                    cat_data["icon"]
                )
                self.categories[category.id] = category
        
        # Import items
        if "items" in data:
            for item_data in data["items"]:
                item = ShopItem(
                    item_data["id"],
                    item_data["name"],
                    item_data["description"],
                    item_data["price"],
                    item_data["icon"],
                    item_data["category"],
                    item_data["game_mode"],
                    item_data.get("level_req", 0),
                    item_data.get("premium", False)
                )
                
                # Set stats if available
                if "stats" in item_data:
                    item.set_stats(item_data["stats"])
                
                # Add tags if available
                if "tags" in item_data and isinstance(item_data["tags"], list):
                    for tag in item_data["tags"]:
                        item.add_tag(tag)
                
                # Set discount if available
                if "discount" in item_data:
                    item.discount = item_data["discount"]
                
                self.items[item.id] = item
                
                # Add item to its category
                if item.category_id in self.categories:
                    self.categories[item.category_id].add_item(item)
        
        self.logger.info("Shop data imported successfully")