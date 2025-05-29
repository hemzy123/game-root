from typing import Dict, List, Optional

class Skill:
    def __init__(self, name: str, description: str, cost: int, prerequisites: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.cost = cost
        self.prerequisites = prerequisites or []

    def __repr__(self):
        return f"<Skill {self.name} (Cost: {self.cost})>"

class SkillTree:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.unlocked_skills: List[str] = []

    def add_skill(self, skill: Skill):
        if skill.name in self.skills:
            raise ValueError(f"Skill '{skill.name}' already exists.")
        self.skills[skill.name] = skill

    def can_unlock(self, skill_name: str) -> bool:
        if skill_name not in self.skills:
            return False
        skill = self.skills[skill_name]
        return all(prereq in self.unlocked_skills for prereq in skill.prerequisites)

    def unlock_skill(self, skill_name: str) -> bool:
        if skill_name in self.unlocked_skills:
            return False
        if self.can_unlock(skill_name):
            self.unlocked_skills.append(skill_name)
            return True
        return False

    def get_unlockable_skills(self) -> List[str]:
        return [
            name for name, skill in self.skills.items()
            if name not in self.unlocked_skills and self.can_unlock(name)
        ]

    def display_tree(self):
        for name, skill in self.skills.items():
            prereq = ', '.join(skill.prerequisites) if skill.prerequisites else "None"
            unlocked = "Unlocked" if name in self.unlocked_skills else "Locked"
            print(f"{name}: {skill.description} (Cost: {skill.cost}) | Prerequisites: {prereq} | {unlocked}")

if __name__ == "__main__":
    tree = SkillTree()

    # Define 100 different skill branch names
    branch_names = [
        "Fire Mastery", "Water Mastery", "Earth Mastery", "Wind Mastery", "Lightning Mastery",
        "Ice Mastery", "Shadow Arts", "Light Arts", "Swordsmanship", "Archery",
        "Alchemy", "Enchanting", "Beast Taming", "Healing", "Necromancy",
        "Berserker", "Assassin", "Paladin", "Druidism", "Summoning",
        "Illusion", "Time Magic", "Space Magic", "Blood Magic", "Curse Magic",
        "Blessing", "Runecrafting", "Elemental Fusion", "Battle Tactics", "Defense Mastery",
        "Agility Training", "Strength Training", "Intellect Training", "Charisma Training", "Luck Training",
        "Mining", "Smithing", "Fishing", "Cooking", "Herbalism",
        "Tracking", "Stealth", "Leadership", "Trading", "Navigation",
        "Music", "Artisan", "Engineering", "Beast Riding", "Mysticism",
        # 50 more branches
        "Pyromancy", "Hydromancy", "Geomancy", "Aeromancy", "Electromancy",
        "Cryomancy", "Umbramancy", "Luminomancy", "Blade Dancing", "Sharpshooting",
        "Potion Brewing", "Sigil Crafting", "Animal Bonding", "Restoration", "Soul Magic",
        "Rage Mastery", "Shadow Strike", "Holy Knight", "Nature's Call", "Spirit Calling",
        "Mirage", "Chronomancy", "Astromancy", "Hemomancy", "Maleficium",
        "Sanctification", "Glyph Mastery", "Elemental Harmony", "Combat Strategy", "Fortification",
        "Reflex Training", "Power Training", "Wisdom Training", "Influence Training", "Fortune Training",
        "Prospecting", "Forging", "Angling", "Gastronomy", "Botany",
        "Scouting", "Infiltration", "Command", "Bartering", "Cartography",
        "Bardic Arts", "Craftsmanship", "Machinery", "Animal Riding", "Occultism"
    ]

    # Generate 100 different skill branches (each branch with 10 named skills)
    for branch in range(100):
        prev_skill = None
        branch_name = branch_names[branch]
        for i in range(10):
            skill_num = i + 1
            skill_name = f"{branch_name} {skill_num}"
            description = f"Level {skill_num} of {branch_name}"
            cost = skill_num
            prerequisites = [prev_skill] if prev_skill else []
            skill = Skill(skill_name, description, cost, prerequisites)
            tree.add_skill(skill)
            prev_skill = skill_name

    # Example: unlock the first skill of each branch
    for branch in range(100):
        skill_name = f"{branch_names[branch]} 1"
        tree.unlock_skill(skill_name)

    tree.display_tree()