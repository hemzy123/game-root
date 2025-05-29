"""
MMORPG Class System Module
Handles all class-related functionality including class definitions, abilities,
progression mechanics, and class-specific attributes.
"""

import json
import os
import logging
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set, Any

# Import relevant game modules
from core.modules.eventManager import EventManager
from core.modules.resourceManager import ResourceManager
from mmorpg.mechanics.skillTree import SkillTree
from mmorpg.mechanics.inventorySystem import InventorySystem

# Set up logging
logger = logging.getLogger(__name__)

class ClassType(Enum):
    """Enumeration of available character classes"""
    WARRIOR = auto()
    MAGE = auto()
    RANGER = auto()
    HEALER = auto()
    ROGUE = auto()
    PALADIN = auto()
    NECROMANCER = auto()
    DRUID = auto()

class ClassRole(Enum):
    """Primary roles that classes can fulfill"""
    TANK = auto()
    DPS = auto()
    HEALER = auto()
    SUPPORT = auto()
    HYBRID = auto()

class AttributeType(Enum):
    """Character attributes affected by class choice"""
    STRENGTH = auto()
    INTELLIGENCE = auto()
    DEXTERITY = auto()
    WISDOM = auto()
    CONSTITUTION = auto()
    CHARISMA = auto()

class ClassSpecialization(Enum):
    """Specializations available for each class at higher levels"""
    # Warrior specializations
    BERSERKER = auto()
    GUARDIAN = auto()
    WARLORD = auto()
    
    # Mage specializations
    ELEMENTALIST = auto()
    ARCHMAGE = auto()
    SPELLBLADE = auto()
    
    # Ranger specializations
    HUNTER = auto()
    MARKSMAN = auto()
    BEASTMASTER = auto()
    
    # Healer specializations
    PRIEST = auto()
    ORACLE = auto()
    TEMPLAR = auto()
    
    # Rogue specializations
    ASSASSIN = auto()
    TRICKSTER = auto()
    SHADOW = auto()
    
    # Paladin specializations
    CRUSADER = auto()
    PROTECTOR = auto()
    AVENGER = auto()
    
    # Necromancer specializations
    REAPER = auto()
    SUMMONER = auto()
    CULTIST = auto()
    
    # Druid specializations
    SHAPESHIFTER = auto()
    NATURALIST = auto()
    GROVE_KEEPER = auto()

class ClassSystem:
    """Main class system handler for character classes and progression"""
    
    def __init__(self, event_manager: EventManager, resource_manager: ResourceManager):
        """Initialize the class system with dependencies
        
        Args:
            event_manager: Game event management system
            resource_manager: Resource loading and caching system
        """
        self.event_manager = event_manager
        self.resource_manager = resource_manager
        self.classes_data = {}
        self.specialization_data = {}
        self.ability_data = {}
        
        # Register event handlers
        self.event_manager.register_handler("player_level_up", self._handle_level_up)
        self.event_manager.register_handler("class_change", self._handle_class_change)
        self.event_manager.register_handler("specialization_selected", self._handle_specialization_selected)
        
        # Load configuration data
        self._load_class_data()
    
    def _load_class_data(self) -> None:
        """Load class configuration data from JSON files"""
        try:
            class_data_path = os.path.join("configs", "data", "classData.json")
            specialization_path = os.path.join("configs", "data", "specializationData.json")
            ability_path = os.path.join("configs", "data", "abilityData.json")
            
            self.classes_data = self.resource_manager.load_json(class_data_path)
            self.specialization_data = self.resource_manager.load_json(specialization_path)
            self.ability_data = self.resource_manager.load_json(ability_path)
            
            logger.info("Successfully loaded class system data")
        except Exception as e:
            logger.error(f"Failed to load class data: {e}")
            # Initialize with default values in case loading fails
            self._initialize_default_data()
    
    def _initialize_default_data(self) -> None:
        """Initialize default class data if configuration loading fails"""
        # Basic default configuration for classes
        self.classes_data = {
            "WARRIOR": {
                "base_attributes": {
                    "STRENGTH": 10,
                    "INTELLIGENCE": 3,
                    "DEXTERITY": 5,
                    "WISDOM": 3,
                    "CONSTITUTION": 8,
                    "CHARISMA": 4
                },
                "roles": ["TANK", "DPS"],
                "weapon_proficiencies": ["sword", "axe", "mace", "shield"],
                "armor_proficiencies": ["plate", "mail"],
                "starting_abilities": ["strike", "defend"],
                "specializations": ["BERSERKER", "GUARDIAN", "WARLORD"],
                "specialization_level": 20
            },
            # Other classes would follow similar structure
        }
        
        # Default specialization data
        self.specialization_data = {
            "BERSERKER": {
                "description": "Offensive warrior focused on dealing maximum damage",
                "attribute_bonuses": {
                    "STRENGTH": 3,
                    "CONSTITUTION": 1
                },
                "abilities": ["rage", "whirlwind", "execute"]
            },
            # Other specializations would follow similar structure
        }
        
        # Default ability data
        self.ability_data = {
            "strike": {
                "name": "Strike",
                "description": "Basic melee attack",
                "damage": 5,
                "cooldown": 1.5,
                "resource_cost": 5,
                "resource_type": "energy",
                "type": "physical",
                "unlock_level": 1
            },
            # Other abilities would follow similar structure
        }
    
    def get_class_info(self, class_type: ClassType) -> Dict[str, Any]:
        """Get information about a specific class
        
        Args:
            class_type: The ClassType to retrieve information for
            
        Returns:
            Dict containing class information
        """
        class_name = class_type.name
        if class_name in self.classes_data:
            return self.classes_data[class_name]
        else:
            logger.warning(f"Class info not found for {class_name}")
            return {}
    
    def get_class_abilities(self, class_type: ClassType, level: int) -> List[Dict[str, Any]]:
        """Get abilities available to a class at the specified level
        
        Args:
            class_type: The ClassType to retrieve abilities for
            level: Character level to check against
            
        Returns:
            List of ability dictionaries available at given level
        """
        class_name = class_type.name
        if class_name not in self.classes_data:
            logger.warning(f"Class not found: {class_name}")
            return []
        
        class_info = self.classes_data[class_name]
        available_abilities = []
        
        # Get base class abilities
        for ability_id in class_info.get("abilities", []):
            if ability_id in self.ability_data:
                ability = self.ability_data[ability_id]
                if ability.get("unlock_level", 1) <= level:
                    available_abilities.append(ability)
        
        return available_abilities
    
    def get_specialization_abilities(self, specialization: ClassSpecialization, level: int) -> List[Dict[str, Any]]:
        """Get abilities available to a specialization at the specified level
        
        Args:
            specialization: The ClassSpecialization to retrieve abilities for
            level: Character level to check against
            
        Returns:
            List of ability dictionaries available at given level
        """
        spec_name = specialization.name
        if spec_name not in self.specialization_data:
            logger.warning(f"Specialization not found: {spec_name}")
            return []
        
        spec_info = self.specialization_data[spec_name]
        available_abilities = []
        
        # Get specialization abilities
        for ability_id in spec_info.get("abilities", []):
            if ability_id in self.ability_data:
                ability = self.ability_data[ability_id]
                if ability.get("unlock_level", 1) <= level:
                    available_abilities.append(ability)
        
        return available_abilities
    
    def calculate_base_attributes(self, class_type: ClassType, level: int) -> Dict[str, int]:
        """Calculate base attributes for a character based on class and level
        
        Args:
            class_type: The ClassType to calculate attributes for
            level: Character level for scaling
            
        Returns:
            Dictionary of attribute values
        """
        class_name = class_type.name
        if class_name not in self.classes_data:
            logger.warning(f"Class not found for attribute calculation: {class_name}")
            return {attr.name: 1 for attr in AttributeType}
        
        class_info = self.classes_data[class_name]
        base_attributes = class_info.get("base_attributes", {})
        
        # Calculate scaled attributes based on level
        scaled_attributes = {}
        for attr_name, base_value in base_attributes.items():
            # Implement class-specific scaling formula
            if attr_name == class_info.get("primary_attribute", ""):
                # Primary attributes scale faster
                scaled_attributes[attr_name] = base_value + (level - 1) * 2
            else:
                # Secondary attributes scale slower
                scaled_attributes[attr_name] = base_value + (level - 1) * 1
        
        return scaled_attributes
    
    def apply_specialization_modifiers(self, attributes: Dict[str, int], 
                                       specialization: Optional[ClassSpecialization]) -> Dict[str, int]:
        """Apply specialization-specific modifiers to attributes
        
        Args:
            attributes: Current attribute values
            specialization: Optional specialization to apply
            
        Returns:
            Modified attribute dictionary
        """
        if not specialization:
            return attributes
        
        spec_name = specialization.name
        if spec_name not in self.specialization_data:
            return attributes
        
        spec_info = self.specialization_data[spec_name]
        modified_attributes = attributes.copy()
        
        # Apply attribute bonuses from specialization
        for attr_name, bonus in spec_info.get("attribute_bonuses", {}).items():
            if attr_name in modified_attributes:
                modified_attributes[attr_name] += bonus
        
        return modified_attributes
    
    def can_equip_weapon(self, class_type: ClassType, weapon_type: str) -> bool:
        """Check if a class can equip a specific weapon type
        
        Args:
            class_type: Character class to check
            weapon_type: Type of weapon to check
            
        Returns:
            True if the class can equip the weapon, False otherwise
        """
        class_name = class_type.name
        if class_name not in self.classes_data:
            return False
        
        proficiencies = self.classes_data[class_name].get("weapon_proficiencies", [])
        return weapon_type.lower() in proficiencies
    
    def can_equip_armor(self, class_type: ClassType, armor_type: str) -> bool:
        """Check if a class can equip a specific armor type
        
        Args:
            class_type: Character class to check
            armor_type: Type of armor to check
            
        Returns:
            True if the class can equip the armor, False otherwise
        """
        class_name = class_type.name
        if class_name not in self.classes_data:
            return False
        
        proficiencies = self.classes_data[class_name].get("armor_proficiencies", [])
        return armor_type.lower() in proficiencies
    
    def get_available_specializations(self, class_type: ClassType) -> List[ClassSpecialization]:
        """Get available specializations for a specific class
        
        Args:
            class_type: The ClassType to get specializations for
            
        Returns:
            List of available ClassSpecialization options
        """
        class_name = class_type.name
        if class_name not in self.classes_data:
            return []
        
        spec_names = self.classes_data[class_name].get("specializations", [])
        return [ClassSpecialization[spec_name] for spec_name in spec_names if spec_name in ClassSpecialization.__members__]
    
    def get_specialization_level(self, class_type: ClassType) -> int:
        """Get level at which specialization becomes available for a class
        
        Args:
            class_type: The ClassType to check
            
        Returns:
            Level at which specializations unlock
        """
        class_name = class_type.name
        if class_name not in self.classes_data:
            return 20  # Default specialization level
        
        return self.classes_data[class_name].get("specialization_level", 20)
    
    def _handle_level_up(self, event_data: Dict[str, Any]) -> None:
        """Handle player level up event
        
        Args:
            event_data: Event data including player entity
        """
        player = event_data.get("player")
        if not player:
            return
        
        new_level = event_data.get("new_level", 1)
        class_type = player.get_class()
        
        # Check if new abilities are unlocked
        new_abilities = []
        for ability_id, ability_data in self.ability_data.items():
            if ability_data.get("unlock_level") == new_level:
                class_list = ability_data.get("classes", [])
                if class_type.name in class_list:
                    new_abilities.append(ability_data["name"])
        
        if new_abilities:
            self.event_manager.trigger_event("abilities_unlocked", {
                "player": player,
                "abilities": new_abilities
            })
        
        # Check if specialization is unlocked
        spec_level = self.get_specialization_level(class_type)
        if new_level == spec_level:
            self.event_manager.trigger_event("specialization_unlocked", {
                "player": player,
                "available_specializations": self.get_available_specializations(class_type)
            })
    
    def _handle_class_change(self, event_data: Dict[str, Any]) -> None:
        """Handle player class change event
        
        Args:
            event_data: Event data including player entity and new class
        """
        player = event_data.get("player")
        new_class = event_data.get("new_class")
        if not player or not new_class:
            return
        
        # Reset abilities and skills
        self.event_manager.trigger_event("abilities_reset", {"player": player})
        
        # Grant starting abilities
        class_info = self.get_class_info(new_class)
        starting_abilities = class_info.get("starting_abilities", [])
        
        self.event_manager.trigger_event("abilities_granted", {
            "player": player,
            "abilities": starting_abilities
        })
        
        # Update player attributes
        base_attributes = self.calculate_base_attributes(new_class, player.level)
        self.event_manager.trigger_event("attributes_updated", {
            "player": player,
            "attributes": base_attributes
        })
    
    def _handle_specialization_selected(self, event_data: Dict[str, Any]) -> None:
        """Handle player specialization selection event
        
        Args:
            event_data: Event data including player entity and chosen specialization
        """
        player = event_data.get("player")
        specialization = event_data.get("specialization")
        if not player or not specialization:
            return
        
        # Grant specialization abilities
        spec_info = self.specialization_data.get(specialization.name, {})
        spec_abilities = spec_info.get("abilities", [])
        
        self.event_manager.trigger_event("abilities_granted", {
            "player": player,
            "abilities": spec_abilities
        })
        
        # Update player attributes with specialization bonuses
        class_type = player.get_class()
        base_attributes = self.calculate_base_attributes(class_type, player.level)
        modified_attributes = self.apply_specialization_modifiers(base_attributes, specialization)
        
        self.event_manager.trigger_event("attributes_updated", {
            "player": player,
            "attributes": modified_attributes
        })

class CharacterClass:
    """Character class implementation that integrates with the class system"""
    
    def __init__(self, class_system: ClassSystem, class_type: ClassType, level: int = 1):
        """Initialize a character class
        
        Args:
            class_system: Reference to the main class system
            class_type: The type of class
            level: Starting level
        """
        self.class_system = class_system
        self.class_type = class_type
        self.level = level
        self.experience = 0
        self.specialization = None
        self.active_abilities = []
        self.passive_abilities = []
        
        # Initialize starting attributes and abilities
        self.attributes = self.class_system.calculate_base_attributes(class_type, level)
        self._initialize_abilities()
    
    def _initialize_abilities(self) -> None:
        """Initialize starting abilities based on class"""
        class_info = self.class_system.get_class_info(self.class_type)
        for ability_id in class_info.get("starting_abilities", []):
            if ability_id in self.class_system.ability_data:
                ability = self.class_system.ability_data[ability_id]
                if ability.get("type") == "passive":
                    self.passive_abilities.append(ability_id)
                else:
                    self.active_abilities.append(ability_id)
    
    def gain_experience(self, amount: int) -> Tuple[bool, int]:
        """Add experience points and check for level up
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            Tuple of (leveled_up, new_level)
        """
        self.experience += amount
        
        # Simple level calculation formula
        # Can be adjusted based on game balance
        new_level = min(50, 1 + int(self.experience / 1000))  # Cap at level 50
        
        if new_level > self.level:
            old_level = self.level
            self.level = new_level
            
            # Update attributes for new level
            self.attributes = self.class_system.calculate_base_attributes(self.class_type, self.level)
            if self.specialization:
                self.attributes = self.class_system.apply_specialization_modifiers(self.attributes, self.specialization)
            
            return True, new_level
        
        return False, self.level
    
    def set_specialization(self, specialization: ClassSpecialization) -> bool:
        """Set character specialization
        
        Args:
            specialization: Specialization to apply
            
        Returns:
            Success or failure
        """
        # Check if specialization is valid for this class
        available_specs = self.class_system.get_available_specializations(self.class_type)
        if specialization not in available_specs:
            return False
        
        # Check if level requirement is met
        spec_level = self.class_system.get_specialization_level(self.class_type)
        if self.level < spec_level:
            return False
        
        self.specialization = specialization
        
        # Update attributes with specialization modifiers
        self.attributes = self.class_system.calculate_base_attributes(self.class_type, self.level)
        self.attributes = self.class_system.apply_specialization_modifiers(self.attributes, specialization)
        
        # Add specialization abilities
        spec_info = self.class_system.specialization_data.get(specialization.name, {})
        for ability_id in spec_info.get("abilities", []):
            if ability_id in self.class_system.ability_data:
                ability = self.class_system.ability_data[ability_id]
                if ability.get("unlock_level", 1) <= self.level:
                    if ability.get("type") == "passive":
                        if ability_id not in self.passive_abilities:
                            self.passive_abilities.append(ability_id)
                    else:
                        if ability_id not in self.active_abilities:
                            self.active_abilities.append(ability_id)
        
        return True
    
    def get_available_abilities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all abilities available to the character
        
        Returns:
            Dictionary with 'active' and 'passive' ability lists
        """
        active = []
        passive = []
        
        # Get class abilities
        class_abilities = self.class_system.get_class_abilities(self.class_type, self.level)
        for ability in class_abilities:
            if ability.get("type") == "passive":
                passive.append(ability)
            else:
                active.append(ability)
        
        # Get specialization abilities if applicable
        if self.specialization:
            spec_abilities = self.class_system.get_specialization_abilities(self.specialization, self.level)
            for ability in spec_abilities:
                if ability.get("type") == "passive":
                    passive.append(ability)
                else:
                    active.append(ability)
        
        return {
            "active": active,
            "passive": passive
        }
    
    def can_use_ability(self, ability_id: str) -> bool:
        """Check if character can use a specific ability
        
        Args:
            ability_id: ID of ability to check
            
        Returns:
            True if ability can be used, False otherwise
        """
        # Check if ability exists
        if ability_id not in self.class_system.ability_data:
            return False
        
        ability = self.class_system.ability_data[ability_id]
        
        # Check level requirement
        if self.level < ability.get("unlock_level", 1):
            return False
        
        # Check class requirement
        required_classes = ability.get("classes", [])
        if required_classes and self.class_type.name not in required_classes:
            # Check specialization requirement
            required_specs = ability.get("specializations", [])
            if not self.specialization or self.specialization.name not in required_specs:
                return False
        
        return True
    
    def get_attribute_value(self, attribute: AttributeType) -> int:
        """Get current value of a specific attribute
        
        Args:
            attribute: Attribute to retrieve
            
        Returns:
            Current attribute value
        """
        return self.attributes.get(attribute.name, 0)
    
    def get_primary_role(self) -> ClassRole:
        """Get primary role of this class/specialization combination
        
        Returns:
            ClassRole representing primary role
        """
        class_info = self.class_system.get_class_info(self.class_type)
        roles = class_info.get("roles", [])
        
        if not roles:
            return ClassRole.DPS  # Default role
        
        # If specialized, check if specialization changes primary role
        if self.specialization:
            spec_info = self.class_system.specialization_data.get(self.specialization.name, {})
            spec_role = spec_info.get("primary_role")
            if spec_role and spec_role in ClassRole.__members__:
                return ClassRole[spec_role]
        
        # Return first role in list as primary
        if roles[0] in ClassRole.__members__:
            return ClassRole[roles[0]]
        else:
            return ClassRole.DPS  # Default role


def test_class_system():
    """Simple test function to demonstrate class system usage"""
    from core.modules.eventManager import EventManager
    from core.modules.resourceManager import ResourceManager
    
    # Create dummy managers for testing
    event_manager = EventManager()
    resource_manager = ResourceManager()
    
    # Initialize class system
    class_system = ClassSystem(event_manager, resource_manager)
    
    # Create a warrior character
    warrior = CharacterClass(class_system, ClassType.WARRIOR, level=1)
    
    # Display initial attributes
    print("Initial warrior attributes:", warrior.attributes)
    
    # Level up the character
    leveled_up, new_level = warrior.gain_experience(20000)
    print(f"Leveled up: {leveled_up}, New level: {new_level}")
    print("New warrior attributes:", warrior.attributes)
    
    # Set specialization
    if warrior.set_specialization(ClassSpecialization.BERSERKER):
        print("Specialized as Berserker")
        print("Specialized warrior attributes:", warrior.attributes)
    
    # Get available abilities
    abilities = warrior.get_available_abilities()
    print("Active abilities:", [a["name"] for a in abilities["active"]])
    print("Passive abilities:", [a["name"] for a in abilities["passive"]])


if __name__ == "__main__":
    # Run test function when executed directly
    test_class_system()