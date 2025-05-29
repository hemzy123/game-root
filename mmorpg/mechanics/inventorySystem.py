"""
MMORPG Inventory System Module
Handles all inventory-related functionality including item management,
storage, equipment, crafting materials, and currency.
"""

import json
import os
import uuid
import time
import logging
import copy
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set, Any, Union, Callable

# Import relevant game modules
from core.modules.eventManager import EventManager
from core.modules.resourceManager import ResourceManager
from mmorpg.mechanics.classSystem import ClassSystem, ClassType

# Set up logging
logger = logging.getLogger(__name__)

class ItemType(Enum):
    """Enumeration of available item types"""
    WEAPON = auto()
    ARMOR = auto()
    ACCESSORY = auto()
    CONSUMABLE = auto()
    MATERIAL = auto()
    QUEST = auto()
    MISCELLANEOUS = auto()
    CONTAINER = auto()
    CURRENCY = auto()
    MOUNT = auto()
    PET = auto()

class ItemRarity(Enum):
    """Rarity levels for items affecting stats and value"""
    COMMON = 0
    UNCOMMON = 1
    RARE = 2
    EPIC = 3
    LEGENDARY = 4
    MYTHIC = 5
    ARTIFACT = 6

class EquipmentSlot(Enum):
    """Available equipment slots on a character"""
    HEAD = auto()
    SHOULDERS = auto()
    CHEST = auto()
    BACK = auto()
    WRISTS = auto()
    HANDS = auto()
    WAIST = auto()
    LEGS = auto()
    FEET = auto()
    NECK = auto()
    FINGER_LEFT = auto()
    FINGER_RIGHT = auto()
    TRINKET_1 = auto()
    TRINKET_2 = auto()
    MAIN_HAND = auto()
    OFF_HAND = auto()
    RANGED = auto()
    
class WeaponType(Enum):
    """Types of weapons that can be equipped"""
    SWORD = auto()
    AXE = auto()
    MACE = auto()
    DAGGER = auto()
    STAFF = auto()
    WAND = auto()
    BOW = auto()
    CROSSBOW = auto()
    SHIELD = auto()
    POLEARM = auto()
    FIST_WEAPON = auto()
    THROWN = auto()
    GUN = auto()
    TOTEM = auto()
    BOOK = auto()
    ORB = auto()

class ArmorType(Enum):
    """Types of armor that can be equipped"""
    CLOTH = auto()
    LEATHER = auto()
    MAIL = auto()
    PLATE = auto()
    
class ConsumableType(Enum):
    """Types of consumable items"""
    POTION = auto()
    FOOD = auto()
    SCROLL = auto()
    ELIXIR = auto()
    ENCHANTMENT = auto()
    
class Item:
    """Base class for all items in the game"""
    
    def __init__(self, item_id: str, name: str, item_type: ItemType, 
                 rarity: ItemRarity = ItemRarity.COMMON, level_req: int = 1, 
                 value: int = 0, stackable: bool = False, max_stack: int = 1, 
                 description: str = "", icon_path: str = "", 
                 unique: bool = False, bind_type: str = None):
        """Initialize a new item
        
        Args:
            item_id: Unique identifier for the item
            name: Display name of the item
            item_type: Type of item from ItemType enum
            rarity: Rarity level affecting value and stats
            level_req: Minimum level required to use this item
            value: Base value in game currency
            stackable: Whether multiple items can stack in one slot
            max_stack: Maximum number of items in a stack if stackable
            description: Item description text
            icon_path: Path to the item's icon texture
            unique: Whether a player can only have one of this item
            bind_type: How the item binds ("pickup", "equip", "account", None)
        """
        self.item_id = item_id
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.level_req = level_req
        self.value = value
        self.stackable = stackable
        self.max_stack = max_stack if stackable else 1
        self.description = description
        self.icon_path = icon_path
        self.unique = unique
        self.bind_type = bind_type
        self.properties = {}  # Additional properties specific to item type
        self.instance_id = str(uuid.uuid4())  # Unique instance ID for this specific item
        self.bound_to = None  # Player ID this item is bound to, if any
        self.created_at = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert item to dictionary for serialization
        
        Returns:
            Dictionary representation of item
        """
        return {
            "item_id": self.item_id,
            "name": self.name,
            "item_type": self.item_type.name,
            "rarity": self.rarity.name,
            "level_req": self.level_req,
            "value": self.value,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "description": self.description,
            "icon_path": self.icon_path,
            "unique": self.unique,
            "bind_type": self.bind_type,
            "properties": self.properties,
            "instance_id": self.instance_id,
            "bound_to": self.bound_to,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """Create an item from a dictionary
        
        Args:
            data: Dictionary containing item data
            
        Returns:
            New Item instance
        """
        item = cls(
            item_id=data["item_id"],
            name=data["name"],
            item_type=ItemType[data["item_type"]],
            rarity=ItemRarity[data["rarity"]],
            level_req=data["level_req"],
            value=data["value"],
            stackable=data["stackable"],
            max_stack=data["max_stack"],
            description=data["description"],
            icon_path=data["icon_path"],
            unique=data["unique"],
            bind_type=data["bind_type"]
        )
        
        item.properties = data.get("properties", {})
        item.instance_id = data.get("instance_id", str(uuid.uuid4()))
        item.bound_to = data.get("bound_to")
        item.created_at = data.get("created_at", time.time())
        
        return item
    
    def bind_to_player(self, player_id: str) -> bool:
        """Bind this item to a specific player if applicable
        
        Args:
            player_id: ID of player to bind to
            
        Returns:
            True if binding was successful, False otherwise
        """
        if not self.bind_type or self.bound_to:
            return False
            
        self.bound_to = player_id
        return True
        
    def can_use(self, player_level: int, player_id: str = None) -> bool:
        """Check if a player can use this item
        
        Args:
            player_level: Level of the player
            player_id: ID of the player checking usage
            
        Returns:
            True if the player can use this item, False otherwise
        """
        # Check level requirement
        if player_level < self.level_req:
            return False
            
        # Check binding restrictions
        if self.bound_to and self.bound_to != player_id:
            return False
            
        return True
        
    def get_sell_value(self) -> int:
        """Calculate the value when selling to a vendor
        
        Returns:
            Sell value in game currency
        """
        # Items typically sell for less than their buy value
        return int(self.value * 0.25)  # 25% of original value
        
    def can_stack_with(self, other: 'Item') -> bool:
        """Check if this item can stack with another
        
        Args:
            other: Another item to check for stacking
            
        Returns:
            True if items can stack together, False otherwise
        """
        if not self.stackable or not other.stackable:
            return False
            
        # Items must be the same type to stack
        if self.item_id != other.item_id:
            return False
            
        # Bound items can only stack with similarly bound items
        if self.bound_to != other.bound_to:
            return False
            
        return True


class Equipment(Item):
    """Specialized item class for equipment (weapons and armor)"""
    
    def __init__(self, item_id: str, name: str, item_type: ItemType,
                 equipment_slot: EquipmentSlot, stats: Dict[str, int] = None,
                 durability: int = 100, max_durability: int = 100,
                 level_req: int = 1, rarity: ItemRarity = ItemRarity.COMMON,
                 value: int = 0, description: str = "", icon_path: str = "",
                 unique: bool = False, bind_type: str = "equip",
                 equipment_type: Union[WeaponType, ArmorType] = None,
                 class_restrictions: List[str] = None):
        """Initialize a new equipment item
        
        Args:
            item_id: Unique identifier for the item
            name: Display name of the item
            item_type: WEAPON or ARMOR from ItemType enum
            equipment_slot: Slot where this equipment can be equipped
            stats: Dictionary of stat bonuses provided by this equipment
            durability: Current durability of the item
            max_durability: Maximum durability of the item
            level_req: Minimum level required to use this item
            rarity: Rarity level affecting value and stats
            value: Base value in game currency
            description: Item description text
            icon_path: Path to the item's icon texture
            unique: Whether a player can only have one of this item
            bind_type: How the item binds ("pickup", "equip", "account", None)
            equipment_type: Specific type of weapon or armor
            class_restrictions: List of class names that can use this equipment
        """
        super().__init__(
            item_id=item_id,
            name=name,
            item_type=item_type,
            rarity=rarity,
            level_req=level_req,
            value=value,
            stackable=False,  # Equipment is never stackable
            max_stack=1,
            description=description,
            icon_path=icon_path,
            unique=unique,
            bind_type=bind_type
        )
        
        self.equipment_slot = equipment_slot
        self.stats = stats or {}
        self.durability = durability
        self.max_durability = max_durability
        self.equipment_type = equipment_type
        self.class_restrictions = class_restrictions or []
        
        # Store equipment-specific properties
        self.properties.update({
            "equipment_slot": equipment_slot.name,
            "stats": self.stats,
            "durability": durability,
            "max_durability": max_durability,
            "equipment_type": equipment_type.name if equipment_type else None,
            "class_restrictions": self.class_restrictions
        })
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Equipment':
        """Create equipment from a dictionary
        
        Args:
            data: Dictionary containing equipment data
            
        Returns:
            New Equipment instance
        """
        props = data.get("properties", {})
        
        # Determine equipment type enum
        equipment_type = None
        if props.get("equipment_type"):
            if data["item_type"] == "WEAPON":
                equipment_type = WeaponType[props["equipment_type"]]
            elif data["item_type"] == "ARMOR":
                equipment_type = ArmorType[props["equipment_type"]]
        
        equipment = cls(
            item_id=data["item_id"],
            name=data["name"],
            item_type=ItemType[data["item_type"]],
            equipment_slot=EquipmentSlot[props["equipment_slot"]],
            stats=props.get("stats", {}),
            durability=props.get("durability", 100),
            max_durability=props.get("max_durability", 100),
            level_req=data["level_req"],
            rarity=ItemRarity[data["rarity"]],
            value=data["value"],
            description=data["description"],
            icon_path=data["icon_path"],
            unique=data["unique"],
            bind_type=data["bind_type"],
            equipment_type=equipment_type,
            class_restrictions=props.get("class_restrictions", [])
        )
        
        equipment.instance_id = data.get("instance_id", str(uuid.uuid4()))
        equipment.bound_to = data.get("bound_to")
        equipment.created_at = data.get("created_at", time.time())
        
        return equipment
    
    def can_be_equipped_by_class(self, class_type: ClassType) -> bool:
        """Check if this equipment can be used by a specific class
        
        Args:
            class_type: Class to check against
            
        Returns:
            True if the class can use this equipment, False otherwise
        """
        if not self.class_restrictions:
            return True  # No restrictions means all classes can use it
            
        return class_type.name in self.class_restrictions
    
    def calculate_repair_cost(self) -> int:
        """Calculate the cost to repair this equipment to full durability
        
        Returns:
            Cost in game currency
        """
        if self.durability >= self.max_durability:
            return 0
            
        damage_percent = (self.max_durability - self.durability) / self.max_durability
        base_repair = self.value * 0.1  # 10% of item value for full repair
        
        return int(base_repair * damage_percent)
    
    def repair(self, amount: int = None) -> int:
        """Repair equipment durability
        
        Args:
            amount: Amount of durability to repair, or None for full repair
            
        Returns:
            Amount of durability repaired
        """
        if amount is None:
            amount = self.max_durability - self.durability
        
        old_durability = self.durability
        self.durability = min(self.durability + amount, self.max_durability)
        repaired = self.durability - old_durability
        
        # Update the properties dictionary
        self.properties["durability"] = self.durability
        
        return repaired
    
    def apply_damage(self, amount: int) -> bool:
        """Apply damage to equipment durability
        
        Args:
            amount: Amount of durability damage to apply
            
        Returns:
            True if item is still usable, False if broken
        """
        self.durability = max(0, self.durability - amount)
        
        # Update the properties dictionary
        self.properties["durability"] = self.durability
        
        return self.durability > 0
    
    def is_broken(self) -> bool:
        """Check if equipment is broken (zero durability)
        
        Returns:
            True if durability is zero, False otherwise
        """
        return self.durability <= 0


class Consumable(Item):
    """Specialized item class for consumable items"""
    
    def __init__(self, item_id: str, name: str, 
                 consumable_type: ConsumableType,
                 effects: List[Dict[str, Any]], cooldown: float = 0,
                 duration: float = 0, charges: int = 1,
                 level_req: int = 1, rarity: ItemRarity = ItemRarity.COMMON,
                 value: int = 0, stackable: bool = True, max_stack: int = 20,
                 description: str = "", icon_path: str = "",
                 unique: bool = False, bind_type: str = None):
        """Initialize a new consumable item
        
        Args:
            item_id: Unique identifier for the item
            name: Display name of the item
            consumable_type: Type of consumable from ConsumableType enum
            effects: List of effects applied when consumed
            cooldown: Cooldown time in seconds before another can be used
            duration: Duration of effects in seconds
            charges: Number of uses before item is consumed
            level_req: Minimum level required to use this item
            rarity: Rarity level affecting value and stats
            value: Base value in game currency
            stackable: Whether multiple items can stack in one slot
            max_stack: Maximum number of items in a stack if stackable
            description: Item description text
            icon_path: Path to the item's icon texture
            unique: Whether a player can only have one of this item
            bind_type: How the item binds ("pickup", "equip", "account", None)
        """
        super().__init__(
            item_id=item_id,
            name=name,
            item_type=ItemType.CONSUMABLE,
            rarity=rarity,
            level_req=level_req,
            value=value,
            stackable=stackable,
            max_stack=max_stack,
            description=description,
            icon_path=icon_path,
            unique=unique,
            bind_type=bind_type
        )
        
        self.consumable_type = consumable_type
        self.effects = effects
        self.cooldown = cooldown
        self.duration = duration
        self.charges = charges
        self.last_used = 0  # Timestamp of last use
        
        # Store consumable-specific properties
        self.properties.update({
            "consumable_type": consumable_type.name,
            "effects": effects,
            "cooldown": cooldown,
            "duration": duration,
            "charges": charges,
            "last_used": self.last_used
        })
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Consumable':
        """Create consumable from a dictionary
        
        Args:
            data: Dictionary containing consumable data
            
        Returns:
            New Consumable instance
        """
        props = data.get("properties", {})
        
        consumable = cls(
            item_id=data["item_id"],
            name=data["name"],
            consumable_type=ConsumableType[props["consumable_type"]],
            effects=props.get("effects", []),
            cooldown=props.get("cooldown", 0),
            duration=props.get("duration", 0),
            charges=props.get("charges", 1),
            level_req=data["level_req"],
            rarity=ItemRarity[data["rarity"]],
            value=data["value"],
            stackable=data["stackable"],
            max_stack=data["max_stack"],
            description=data["description"],
            icon_path=data["icon_path"],
            unique=data["unique"],
            bind_type=data["bind_type"]
        )
        
        consumable.instance_id = data.get("instance_id", str(uuid.uuid4()))
        consumable.bound_to = data.get("bound_to")
        consumable.created_at = data.get("created_at", time.time())
        consumable.last_used = props.get("last_used", 0)
        
        return consumable
    
    def use(self, target: Any = None) -> Tuple[bool, Dict[str, Any]]:
        """Use the consumable item
        
        Args:
            target: Optional target entity for the consumable effect
            
        Returns:
            Tuple of (success, effects_data)
        """
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_used < self.cooldown:
            remaining = self.cooldown - (current_time - self.last_used)
            return (False, {"error": "on_cooldown", "remaining": remaining})
        
        # Decrement charges
        self.charges -= 1
        self.last_used = current_time
        
        # Update properties
        self.properties["charges"] = self.charges
        self.properties["last_used"] = self.last_used
        
        # Return success and effects
        return (True, {
            "effects": self.effects,
            "duration": self.duration,
            "consumed": self.charges <= 0
        })
    
    def is_on_cooldown(self) -> Tuple[bool, float]:
        """Check if this consumable is on cooldown
        
        Returns:
            Tuple of (on_cooldown, remaining_cooldown)
        """
        if self.cooldown <= 0:
            return (False, 0)
            
        current_time = time.time()
        elapsed = current_time - self.last_used
        
        if elapsed < self.cooldown:
            return (True, self.cooldown - elapsed)
            
        return (False, 0)


class ItemStack:
    """Represents a stack of items in an inventory slot"""
    
    def __init__(self, item: Item, quantity: int = 1):
        """Initialize a new item stack
        
        Args:
            item: The item in this stack
            quantity: Number of items in the stack
        """
        self.item = item
        self.quantity = min(quantity, item.max_stack if item.stackable else 1)
    
    def add(self, count: int = 1) -> int:
        """Add items to this stack
        
        Args:
            count: Number of items to add
            
        Returns:
            Number of items that couldn't be added (overflow)
        """
        if not self.item.stackable:
            return count
            
        space_left = self.item.max_stack - self.quantity
        can_add = min(count, space_left)
        
        self.quantity += can_add
        return count - can_add
    
    def remove(self, count: int = 1) -> int:
        """Remove items from this stack
        
        Args:
            count: Number of items to remove
            
        Returns:
            Number of items actually removed
        """
        can_remove = min(count, self.quantity)
        self.quantity -= can_remove
        return can_remove
    
    def is_empty(self) -> bool:
        """Check if this stack is empty
        
        Returns:
            True if quantity is zero, False otherwise
        """
        return self.quantity <= 0
    
    def is_full(self) -> bool:
        """Check if this stack is at maximum capacity
        
        Returns:
            True if stack is full, False otherwise
        """
        return not self.item.stackable or self.quantity >= self.item.max_stack
    
    def split(self, count: int) -> Optional['ItemStack']:
        """Split this stack into two stacks
        
        Args:
            count: Number of items to split into new stack
            
        Returns:
            New ItemStack with split items, or None if split failed
        """
        if count <= 0 or count >= self.quantity:
            return None
            
        # Create a copy of the item for the new stack
        new_item = copy.deepcopy(self.item)
        
        # Create new stack with copied item
        new_stack = ItemStack(new_item, count)
        
        # Remove items from this stack
        self.quantity -= count
        
        return new_stack
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stack to dictionary for serialization
        
        Returns:
            Dictionary representation of stack
        """
        return {
            "item": self.item.to_dict(),
            "quantity": self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ItemStack':
        """Create a stack from a dictionary
        
        Args:
            data: Dictionary containing stack data
            
        Returns:
            New ItemStack instance
        """
        item_data = data["item"]
        
        # Create appropriate item type based on item_type
        if item_data["item_type"] == "WEAPON" or item_data["item_type"] == "ARMOR":
            item = Equipment.from_dict(item_data)
        elif item_data["item_type"] == "CONSUMABLE":
            item = Consumable.from_dict(item_data)
        else:
            item = Item.from_dict(item_data)
        
        return cls(item, data["quantity"])


class Inventory:
    """Main inventory class for storing and managing items"""
    
    def __init__(self, owner_id: str, max_slots: int = 30, gold: int = 0, 
                 event_manager: Optional[EventManager] = None):
        """Initialize a new inventory
        
        Args:
            owner_id: ID of player or entity that owns this inventory
            max_slots: Maximum number of slots in the inventory
            gold: Starting amount of gold currency
            event_manager: Optional event manager for inventory events
        """
        self.owner_id = owner_id
        self.max_slots = max_slots
        self.gold = gold
        self.event_manager = event_manager
        self.slots: List[Optional[ItemStack]] = [None] * max_slots
        self.equipment_slots: Dict[EquipmentSlot, Optional[Equipment]] = {
            slot: None for slot in EquipmentSlot
        }
        self.currencies: Dict[str, int] = {"gold": gold}
    
    def add_item(self, item: Item, quantity: int = 1, slot_index: Optional[int] = None) -> Dict[str, Any]:
        """Add an item to the inventory
        
        Args:
            item: Item to add
            quantity: Number of items to add
            slot_index: Optional specific slot to add to
            
        Returns:
            Result dictionary with status and details
        """
        if quantity <= 0:
            return {"success": False, "error": "invalid_quantity"}
        
        # Check if item is unique and already exists in inventory
        if item.unique and self.has_item(item.item_id):
            return {"success": False, "error": "unique_item_exists"}
        
        remaining = quantity
        result = {"success": True, "added": 0, "remaining": 0}
        
        # If a specific slot was requested
        if slot_index is not None:
            if not self.is_valid_slot(slot_index):
                return {"success": False, "error": "invalid_slot"}
                
            stack = self.slots[slot_index]
            
            # Empty slot or matching item that can be stacked
            if stack is None:
                self.slots[slot_index] = ItemStack(item, quantity)
                result["added"] = quantity
                remaining = 0
            elif stack.item.can_stack_with(item):
                overflow = stack.add(quantity)
                result["added"] = quantity - overflow
                remaining = overflow
            else:
                return {"success": False, "error": "slot_occupied"}
        else:
            # Try to find existing stacks of the same item first
            if item.stackable:
                for i, stack in enumerate(self.slots):
                    if stack and stack.item.can_stack_with(item) and not stack.is_full():
                        overflow = stack.add(remaining)
                        result["added"] += remaining - overflow
                        remaining = overflow
                        
                        if remaining == 0:
                            break
            
            # If we still have items to add, find empty slots
            if remaining > 0:
                for i, stack in enumerate(self.slots):
                    if stack is None:
                        # How many can we put in this slot?
                        to_add = min(remaining, item.max_stack if item.stackable else 1)
                        
                        # Create a new instance for non-stackable items
                        slot_item = item if item.stackable else copy.deepcopy(item)
                        self.slots[i] = ItemStack(slot_item, to_add)
                        
                        result["added"] += to_add
                        remaining -= to_add
                        
                        if remaining == 0:
                            break
        
        result["remaining"] = remaining
        
        # If we were able to add at least some items
        if result["added"] > 0:
            # Trigger event
            if self.event_manager:
                self.event_manager.trigger_event("inventory_item_added", {
                    "owner_id": self.owner_id,
                    "item_id": item.item_id,
                    "quantity": result["added"]
                })
            
            # If item binds on pickup and was successfully added
            if item.bind_type == "pickup" and not item.bound_to:
                item.bind_to_player(self.owner_id)
        
        return result
    
    def remove_item(self, item_id: str, quantity: int = 1, slot_index: Optional[int] = None) -> Dict[str, Any]:
        """Remove an item from the inventory
        
        Args:
            item_id: ID of the item to remove
            quantity: Number of items to remove
            slot_index: Optional specific slot to remove from
            
        Returns:
            Result dictionary with status and details
        """
        if quantity <= 0:
            return {"success": False, "error": "invalid_quantity"}
        
        result = {"success": True, "removed": 0, "remaining": quantity}
        
        # If a specific slot was requested
        if slot_index is not None:
            if not self.is_valid_slot(slot_index):
                return {"success": False, "error": "invalid_slot"}
                
            stack = self.slots[slot_index]
            
            if stack is None or stack.item.item_id != item_id:
                return {"success": False, "error": "item_not_found"}
                
            removed = stack.remove(quantity)
            result["removed"] = removed
            result["remaining"] = quantity - removed
            
            # Clean up empty stack
            if stack.is_empty():
                self.slots[slot_index] = None
        else:
            # Remove from any slots containing the item
            remaining = quantity
            
            for i, stack in enumerate(self.slots):
                if stack and stack.item.item_id == item_id:
                    removed = stack.remove(remaining)
                    result["removed"] += removed
                    remaining -= removed
                    
                    # Clean up empty stack
                    if stack.is_empty():
                        self.slots[i] = None
                    
                    if remaining == 0:
                        break
            
            result["remaining"] = remaining
        
        # If we removed any items
        if result["removed"] > 0 and self.event_manager:
            self.event_manager.trigger_event("inventory_item_removed", {
                "owner_id": self.owner_id,
                "item_id": item_id,
                "quantity": result["removed"]
            })
        
        return result
    
    def move_item(self, from_slot: int, to_slot: int, quantity: Optional[int] = None) -> Dict[str, Any]:
        """Move an item between inventory slots
        
        Args:
            from_slot: Source slot index
            to_slot: Destination slot index
            quantity: Optional quantity to move (for splitting stacks)
            
        Returns:
            Result dictionary with status and details
        """
        # Validate slot indices
        if not self.is_valid_slot(from_slot) or not self.is_valid_slot(to_slot):
            return {"success": False, "error": "invalid_slot"}
            
        # Check if source slot has an item
        if self.slots[from_slot] is None:
            return {"success": False, "error": "source_slot_empty"}
            
        # If source and destination are the same, do nothing
        if from_slot == to_slot:
            return {"success": True, "moved": 0}
            
        source_stack = self.slots[from_slot]
        dest_stack = self.slots[to_slot]
        
        # Determine quantity to move
        move_quantity = quantity if quantity is not None else source_stack.quantity
        
        # Validate quantity
        if move_quantity <= 0 or move_quantity > source_stack.quantity:
            return {"success": False, "error": "invalid_quantity"}
            
        result = {"success": True, "moved": 0}
        
        # If destination is empty
        if dest_stack is None:
            if move_quantity == source_stack.quantity:
                # Move the entire stack
                self.slots[to_slot] = source_stack
                self.slots[from_slot] = None
                result["moved"] = move_quantity
            else:
                # Split the stack
                new_stack = source_stack.split(move_quantity)
                if new_stack:
                    self.slots[to_slot] = new_stack
                    result["moved"] = move_quantity
                else:
                    return {"success": False, "error": "split_failed"}
        else:
            # Try to merge stacks
            if source_stack.item.can_stack_with(dest_stack.item):
                # Calculate how many items we can add to destination
                can_add = min(move_quantity, dest_stack.item.max_stack - dest_stack.quantity)
                
                if can_add > 0:
                    # Add to destination
                    dest_stack.add(can_add)
                    
                    # Remove from source
                    source_stack.remove(can_add)
                    
                    # Clean up empty source stack
                    if source_stack.is_empty():
                        self.slots[from_slot] = None
                        
                    result["moved"] = can_add
                else:
                    return {"success": False, "error": "destination_full"}
            else:
                # Swap items
                if move_quantity == source_stack.quantity:
                    self.slots[from_slot], self.slots[to_slot] = self.slots[to_slot], self.slots[from_slot]
                    result["moved"] = move_quantity
                    result["swapped"] = True
                else:
                    return {"success": False, "error": "cannot_merge_different_items"}
        
        # Trigger event
        if self.event_manager and result["moved"] > 0:
            self.event_manager.trigger_event("inventory_item_moved", {
                "owner_id": self.owner_id,
                "from_slot": from_slot,
                "to_slot": to_slot,
                "quantity": result["moved"]
            })
            
        return result
    
    def is_valid_slot(self, slot_index: int) -> bool:
        """Check if a slot index is valid for this inventory
        
        Args:
            slot_index: Slot index to check
            
        Returns:
            True if slot index is valid, False otherwise
        """
        return 0 <= slot_index < self.max_slots
    
    def has_item(self, item_id: str, required_quantity: int = 1) -> bool:
        """Check if inventory has a specific item
        
        Args:
            item_id: ID of item to check for
            required_quantity: Minimum quantity required
            
        Returns:
            True if inventory has enough of the item, False otherwise
        """
        total_quantity = 0
        
        for stack in self.slots:
            if stack and stack.item.item_id == item_id:
                total_quantity += stack.quantity
                
                if total_quantity >= required_quantity:
                    return True
                    
        return False
    
    def count_item(self, item_id: str) -> int:
        """Count how many of a specific item are in the inventory
        
        Args:
            item_id: ID of item to count
            
        Returns:
            Total quantity of the item in inventory
        """
        total_quantity = 0
        
        for stack in self.slots:
            if stack and stack.item.item_id == item_id:
                total_quantity += stack.quantity
                
        return total_quantity
    
    def get_first_item_slot(self, item_id: str) -> Optional[int]:
        """Find the first slot containing a specific item
        
        Args:
            item_id: ID of item to find
            
        Returns:
            Slot index or None if not found
        """
        for i, stack in enumerate(self.slots):
            if stack and stack.item.item_id == item_id:
                return i
                
        return None
    
    def get_empty_slot(self) -> Optional[int]:
        """Find the first empty inventory slot
        
        Returns:
            Slot index or None if inventory is full
        """
        for i, stack in enumerate(self.slots):
            if stack is None:
                return i
                
        return None
    
    def is_full(self) -> bool:
        """Check if inventory is full
        
        Returns:
            True if no empty slots remain, False otherwise
        """
        return self.get_empty_slot() is None
    
    def get_free_slots(self) -> int:
        """Count number of empty slots in inventory
        
        Returns:
            Number of empty slots
        """
        return sum(1 for stack in self.slots if stack is None)
    
    def equip_item(self, slot_index: int, player_level: int, player_class: ClassType) -> Dict[str, Any]:
        """Equip an item from inventory to equipment slot
        
        Args:
            slot_index: Inventory slot containing item to equip
            player_level: Current level of the player
            player_class: Class of the player
            
        Returns:
            Result dictionary with status and details
        """
        if not self.is_valid_slot(slot_index):
            return {"success": False, "error": "invalid_slot"}
            
        stack = self.slots[slot_index]
        
        if stack is None:
            return {"success": False, "error": "slot_empty"}
            
        item = stack.item
        
        # Verify the item is equipment
        if item.item_type not in (ItemType.WEAPON, ItemType.ARMOR):
            return {"success": False, "error": "item_not_equipment"}
            
        # Ensure it's actually an Equipment instance
        if not isinstance(item, Equipment):
            return {"success": False, "error": "invalid_equipment_type"}
            
        # Check level requirement
        if player_level < item.level_req:
            return {"success": False, "error": "level_requirement_not_met"}
            
        # Check class restrictions
        if not item.can_be_equipped_by_class(player_class):
            return {"success": False, "error": "class_restriction"}
            
        # Check if item is broken
        if item.is_broken():
            return {"success": False, "error": "item_broken"}
            
        # Get the equipment slot
        equip_slot = item.equipment_slot
        
        # Check if something is already equipped in that slot
        currently_equipped = self.equipment_slots[equip_slot]
        
        result = {"success": True, "equipped": item.name}
        
        # If something is equipped, unequip it first
        if currently_equipped:
            # Find an empty inventory slot
            empty_slot = self.get_empty_slot()
            
            # If inventory is full, can't unequip
            if empty_slot is None:
                return {"success": False, "error": "inventory_full"}
                
            # Move currently equipped item to inventory
            self.slots[empty_slot] = ItemStack(currently_equipped)
            result["unequipped"] = currently_equipped.name
            result["unequipped_to_slot"] = empty_slot
        
        # Equip the new item
        self.equipment_slots[equip_slot] = item
        
        # Remove from inventory
        self.slots[slot_index] = None
        
        # Bind item if it binds on equip
        if item.bind_type == "equip" and not item.bound_to:
            item.bind_to_player(self.owner_id)
        
        # Trigger event
        if self.event_manager:
            self.event_manager.trigger_event("item_equipped", {
                "owner_id": self.owner_id,
                "item_id": item.item_id,
                "slot": equip_slot.name
            })
        
        return result
    
    def unequip_item(self, equip_slot: EquipmentSlot, slot_index: Optional[int] = None) -> Dict[str, Any]:
        """Unequip an item from equipment slot to inventory
        
        Args:
            equip_slot: Equipment slot to unequip from
            slot_index: Optional specific inventory slot to place item in
            
        Returns:
            Result dictionary with status and details
        """
        # Check if something is equipped in that slot
        item = self.equipment_slots[equip_slot]
        
        if item is None:
            return {"success": False, "error": "nothing_equipped"}
        
        # Determine destination slot
        if slot_index is not None:
            if not self.is_valid_slot(slot_index):
                return {"success": False, "error": "invalid_slot"}
                
            if self.slots[slot_index] is not None:
                return {"success": False, "error": "slot_occupied"}
                
            dest_slot = slot_index
        else:
            # Find an empty inventory slot
            dest_slot = self.get_empty_slot()
            
            # If inventory is full, can't unequip
            if dest_slot is None:
                return {"success": False, "error": "inventory_full"}
        
        # Move equipped item to inventory
        self.slots[dest_slot] = ItemStack(item)
        
        # Clear equipment slot
        self.equipment_slots[equip_slot] = None
        
        # Trigger event
        if self.event_manager:
            self.event_manager.trigger_event("item_unequipped", {
                "owner_id": self.owner_id,
                "item_id": item.item_id,
                "slot": equip_slot.name,
                "to_slot": dest_slot
            })
        
        return {
            "success": True,
            "unequipped": item.name,
            "to_slot": dest_slot
        }
    
    def get_equipment_stats(self) -> Dict[str, int]:
        """Calculate total stats from all equipped items
        
        Returns:
            Dictionary of stat name to total value
        """
        total_stats = {}
        
        for slot, item in self.equipment_slots.items():
            if item and hasattr(item, 'stats') and not item.is_broken():
                for stat, value in item.stats.items():
                    if stat in total_stats:
                        total_stats[stat] += value
                    else:
                        total_stats[stat] = value
        
        return total_stats
    
    def add_currency(self, currency_type: str, amount: int) -> bool:
        """Add currency to the inventory
        
        Args:
            currency_type: Type of currency to add
            amount: Amount to add
            
        Returns:
            True if successful, False otherwise
        """
        if amount <= 0:
            return False
            
        if currency_type in self.currencies:
            self.currencies[currency_type] += amount
        else:
            self.currencies[currency_type] = amount
            
        # Special case for gold which has a direct property
        if currency_type == "gold":
            self.gold = self.currencies["gold"]
            
        # Trigger event
        if self.event_manager:
            self.event_manager.trigger_event("currency_added", {
                "owner_id": self.owner_id,
                "currency_type": currency_type,
                "amount": amount,
                "new_balance": self.currencies[currency_type]
            })
            
        return True
    
    def remove_currency(self, currency_type: str, amount: int) -> bool:
        """Remove currency from the inventory
        
        Args:
            currency_type: Type of currency to remove
            amount: Amount to remove
            
        Returns:
            True if successful, False otherwise
        """
        if amount <= 0:
            return False
            
        if currency_type not in self.currencies or self.currencies[currency_type] < amount:
            return False
            
        self.currencies[currency_type] -= amount
        
        # Special case for gold which has a direct property
        if currency_type == "gold":
            self.gold = self.currencies["gold"]
            
        # Trigger event
        if self.event_manager:
            self.event_manager.trigger_event("currency_removed", {
                "owner_id": self.owner_id,
                "currency_type": currency_type,
                "amount": amount,
                "new_balance": self.currencies[currency_type]
            })
            
        return True
    
    def has_currency(self, currency_type: str, amount: int) -> bool:
        """Check if inventory has enough of a currency
        
        Args:
            currency_type: Type of currency to check
            amount: Minimum amount required
            
        Returns:
            True if inventory has enough currency, False otherwise
        """
        return currency_type in self.currencies and self.currencies[currency_type] >= amount
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert inventory to dictionary for serialization
        
        Returns:
            Dictionary representation of inventory
        """
        return {
            "owner_id": self.owner_id,
            "max_slots": self.max_slots,
            "slots": [stack.to_dict() if stack else None for stack in self.slots],
            "equipment_slots": {
                slot.name: item.to_dict() if item else None
                for slot, item in self.equipment_slots.items()
            },
            "currencies": self.currencies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], event_manager: Optional[EventManager] = None) -> 'Inventory':
        """Create inventory from a dictionary
        
        Args:
            data: Dictionary containing inventory data
            event_manager: Optional event manager for inventory events
            
        Returns:
            New Inventory instance
        """
        inventory = cls(
            owner_id=data["owner_id"],
            max_slots=data["max_slots"],
            gold=data.get("currencies", {}).get("gold", 0),
            event_manager=event_manager
        )
        
        # Load slots
        for i, slot_data in enumerate(data["slots"]):
            if slot_data:
                inventory.slots[i] = ItemStack.from_dict(slot_data)
        
        # Load equipment slots
        for slot_name, item_data in data["equipment_slots"].items():
            if item_data:
                slot = EquipmentSlot[slot_name]
                inventory.equipment_slots[slot] = Equipment.from_dict(item_data)
        
        # Load currencies
        inventory.currencies = data.get("currencies", {"gold": inventory.gold})
        
        return inventory
    
    def clear(self) -> None:
        """Clear all items from inventory and equipment"""
        self.slots = [None] * self.max_slots
        self.equipment_slots = {slot: None for slot in EquipmentSlot}
        
        if self.event_manager:
            self.event_manager.trigger_event("inventory_cleared", {
                "owner_id": self.owner_id
            })


class InventoryManager:
    """Manages all inventories in the game"""
    
    def __init__(self, resource_manager: ResourceManager, event_manager: EventManager):
        """Initialize inventory manager
        
        Args:
            resource_manager: Resource manager for loading item templates
            event_manager: Event manager for inventory events
        """
        self.resource_manager = resource_manager
        self.event_manager = event_manager
        self.inventories: Dict[str, Inventory] = {}
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        
        # Load item templates
        self._load_item_templates()
        
        # Register event handlers
        self._register_events()
    
    def _load_item_templates(self) -> None:
        """Load item templates from data files"""
        try:
            # Load base items
            items_data = self.resource_manager.load_json("data/items/items.json")
            
            # Load equipment
            equipment_data = self.resource_manager.load_json("data/items/equipment.json")
            
            # Load consumables
            consumable_data = self.resource_manager.load_json("data/items/consumables.json")
            
            # Combine all templates
            self.item_templates.update(items_data)
            self.item_templates.update(equipment_data)
            self.item_templates.update(consumable_data)
            
            logger.info(f"Loaded {len(self.item_templates)} item templates")
        except Exception as e:
            logger.error(f"Error loading item templates: {e}")
    
    def _register_events(self) -> None:
        """Register event handlers"""
        self.event_manager.register_handler("player_created", self._on_player_created)
        self.event_manager.register_handler("player_level_up", self._on_player_level_up)
    
    def _on_player_created(self, event_data: Dict[str, Any]) -> None:
        """Handle player created event
        
        Args:
            event_data: Event data containing player info
        """
        player_id = event_data["player_id"]
        
        # Create player inventory
        self.create_inventory(player_id, 30, 100)  # 30 slots, 100 starting gold
        
        # Add starter items based on player class
        if "class_type" in event_data:
            self._add_starter_items(player_id, event_data["class_type"])
    
    def _on_player_level_up(self, event_data: Dict[str, Any]) -> None:
        """Handle player level up event
        
        Args:
            event_data: Event data containing player info
        """
        player_id = event_data["player_id"]
        new_level = event_data["new_level"]
        
        # Check if inventory needs to be expanded at certain levels
        if new_level in (10, 20, 30, 40, 50):
            self.expand_inventory(player_id, 5)  # Add 5 slots at milestone levels
    
    def _add_starter_items(self, player_id: str, class_type: ClassType) -> None:
        """Add starter items based on player class
        
        Args:
            player_id: ID of player
            class_type: Class of the player
        """
        inventory = self.get_inventory(player_id)
        if not inventory:
            return
            
        # Add common starter items
        self.add_item_to_inventory(player_id, "health_potion_minor", 5)
        self.add_item_to_inventory(player_id, "basic_food", 5)
        
        # Add class-specific starter gear
        if class_type == ClassType.WARRIOR:
            self.add_item_to_inventory(player_id, "starter_sword", 1)
            self.add_item_to_inventory(player_id, "starter_shield", 1)
        elif class_type == ClassType.MAGE:
            self.add_item_to_inventory(player_id, "starter_staff", 1)
            self.add_item_to_inventory(player_id, "starter_spellbook", 1)
        elif class_type == ClassType.ROGUE:
            self.add_item_to_inventory(player_id, "starter_daggers", 1)
            self.add_item_to_inventory(player_id, "starter_leather_armor", 1)
        # Add more class-specific items as needed
    
    def create_inventory(self, owner_id: str, max_slots: int = 30, 
                         starting_gold: int = 0) -> Inventory:
        """Create a new inventory
        
        Args:
            owner_id: ID of player or entity that owns this inventory
            max_slots: Maximum number of slots in the inventory
            starting_gold: Starting amount of gold currency
            
        Returns:
            New Inventory instance
        """
        inventory = Inventory(
            owner_id=owner_id,
            max_slots=max_slots,
            gold=starting_gold,
            event_manager=self.event_manager
        )
        
        self.inventories[owner_id] = inventory
        return inventory
    
    def get_inventory(self, owner_id: str) -> Optional[Inventory]:
        """Get an inventory by owner ID
        
        Args:
            owner_id: ID of inventory owner
            
        Returns:
            Inventory instance or None if not found
        """
        return self.inventories.get(owner_id)
    
    def create_item(self, item_id: str) -> Optional[Item]:
        """Create a new item from template
        
        Args:
            item_id: ID of item template
            
        Returns:
            New Item instance or None if template not found
        """
        if item_id not in self.item_templates:
            logger.error(f"Item template {item_id} not found")
            return None
        
        template = self.item_templates[item_id]
        item_type = ItemType[template["item_type"]]
        
        # Create appropriate item type based on item_type
        if item_type == ItemType.WEAPON or item_type == ItemType.ARMOR:
            props = template.get("properties", {})
            equipment_slot = EquipmentSlot[props["equipment_slot"]]
            
            if item_type == ItemType.WEAPON:
                equipment_type = WeaponType[props["equipment_type"]]
            else:
                equipment_type = ArmorType[props["equipment_type"]]
                
            return Equipment(
                item_id=item_id,
                name=template["name"],
                item_type=item_type,
                equipment_slot=equipment_slot,
                stats=props.get("stats", {}),
                durability=props.get("durability", 100),
                max_durability=props.get("max_durability", 100),
                level_req=template["level_req"],
                rarity=ItemRarity[template["rarity"]],
                value=template["value"],
                description=template["description"],
                icon_path=template["icon_path"],
                unique=template.get("unique", False),
                bind_type=template.get("bind_type"),
                equipment_type=equipment_type,
                class_restrictions=props.get("class_restrictions", [])
            )
        elif item_type == ItemType.CONSUMABLE:
            props = template.get("properties", {})
            
            return Consumable(
                item_id=item_id,
                name=template["name"],
                consumable_type=ConsumableType[props["consumable_type"]],
                effects=props.get("effects", []),
                cooldown=props.get("cooldown", 0),
                duration=props.get("duration", 0),
                charges=props.get("charges", 1),
                level_req=template["level_req"],
                rarity=ItemRarity[template["rarity"]],
                value=template["value"],
                stackable=template.get("stackable", True),
                max_stack=template.get("max_stack", 20),
                description=template["description"],
                icon_path=template["icon_path"],
                unique=template.get("unique", False),
                bind_type=template.get("bind_type")
            )
        else:
            return Item(
                item_id=item_id,
                name=template["name"],
                item_type=item_type,
                rarity=ItemRarity[template["rarity"]],
                level_req=template["level_req"],
                value=template["value"],
                stackable=template.get("stackable", False),
                max_stack=template.get("max_stack", 1),
                description=template["description"],
                icon_path=template["icon_path"],
                unique=template.get("unique", False),
                bind_type=template.get("bind_type")
            )
    
    def add_item_to_inventory(self, owner_id: str, item_id: str, 
                             quantity: int = 1) -> Dict[str, Any]:
        """Add an item to an inventory from template
        
        Args:
            owner_id: ID of inventory owner
            item_id: ID of item template
            quantity: Number of items to add
            
        Returns:
            Result dictionary with status and details
        """
        inventory = self.get_inventory(owner_id)
        if not inventory:
            return {"success": False, "error": "inventory_not_found"}
            
        item = self.create_item(item_id)
        if not item:
            return {"success": False, "error": "item_not_found"}
            
        return inventory.add_item(item, quantity)
    
    def save_all_inventories(self, save_dir: str) -> bool:
        """Save all inventories to files
        
        Args:
            save_dir: Directory to save inventory files
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            for owner_id, inventory in self.inventories.items():
                filepath = os.path.join(save_dir, f"{owner_id}_inventory.json")
                with open(filepath, 'w') as f:
                    json.dump(inventory.to_dict(), f, indent=2)
                    
            logger.info(f"Saved {len(self.inventories)} inventories to {save_dir}")
            return True
        except Exception as e:
            logger.error(f"Error saving inventories: {e}")
            return False
    
    def load_all_inventories(self, save_dir: str) -> bool:
        """Load all inventories from files
        
        Args:
            save_dir: Directory containing inventory files
            
        Returns:
            True if load was successful, False otherwise
        """
        try:
            if not os.path.exists(save_dir):
                logger.warning(f"Inventory save directory {save_dir} does not exist")
                return False
                
            inventory_files = [f for f in os.listdir(save_dir) if f.endswith("_inventory.json")]
            
            for filename in inventory_files:
                filepath = os.path.join(save_dir, filename)
                owner_id = filename.replace("_inventory.json", "")
                
                with open(filepath, 'r') as f:
                    inventory_data = json.load(f)
                    self.inventories[owner_id] = Inventory.from_dict(
                        inventory_data, self.event_manager
                    )
                    
            logger.info(f"Loaded {len(inventory_files)} inventories from {save_dir}")
            return True
        except Exception as e:
            logger.error(f"Error loading inventories: {e}")
            return False
    
    def expand_inventory(self, owner_id: str, additional_slots: int) -> bool:
        """Expand an inventory's capacity
        
        Args:
            owner_id: ID of inventory owner
            additional_slots: Number of slots to add
            
        Returns:
            True if expansion was successful, False otherwise
        """
        inventory = self.get_inventory(owner_id)
        if not inventory:
            return False
            
        if additional_slots <= 0:
            return False
            
        old_max = inventory.max_slots
        inventory.max_slots += additional_slots
        
        # Add new empty slots
        inventory.slots.extend([None] * additional_slots)
        
        # Trigger event
        self.event_manager.trigger_event("inventory_expanded", {
            "owner_id": owner_id,
            "old_size": old_max,
            "new_size": inventory.max_slots,
            "added_slots": additional_slots
        })
        
        return True


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create resource and event managers
    resource_mgr = ResourceManager("resources")
    event_mgr = EventManager()
    
    # Create inventory manager
    inv_mgr = InventoryManager(resource_mgr, event_mgr)
    
    # Create a player inventory
    player_inv = inv_mgr.create_inventory("player1", 20, 500)
    
    # Add some items
    inv_mgr.add_item_to_inventory("player1", "health_potion_minor", 5)
    inv_mgr.add_item_to_inventory("player1", "basic_sword", 1)
    
    # Display inventory
    print(f"Player has {player_inv.count_item('health_potion_minor')} health potions")
    print(f"Player gold: {player_inv.gold}")
    
    # Save inventories
    inv_mgr.save_all_inventories("saves/inventories")