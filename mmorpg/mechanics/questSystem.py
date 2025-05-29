from abc import ABC, abstractmethod
from typing import List, Dict, Any
import random
# Quest Objective base class
class QuestObjective(ABC):
    @abstractmethod
    def is_completed(self, player_data: Dict[str, Any]) -> bool:
        pass

# Kill Objective
class KillObjective(QuestObjective):
    def __init__(self, monster: str, amount: int):
        self.monster = monster
        self.amount = amount

    def is_completed(self, player_data: Dict[str, Any]) -> bool:
        return player_data.get(f"kill_{self.monster}", 0) >= self.amount

# Collect Objective
class CollectObjective(QuestObjective):
    def __init__(self, item: str, amount: int):
        self.item = item
        self.amount = amount

    def is_completed(self, player_data: Dict[str, Any]) -> bool:
        return player_data.get(f"collect_{self.item}", 0) >= self.amount

# Explore Objective
class ExploreObjective(QuestObjective):
    def __init__(self, area: str):
        self.area = area

    def is_completed(self, player_data: Dict[str, Any]) -> bool:
        return player_data.get(f"explore_{self.area}", False)

# Dungeon Objective
class DungeonObjective(QuestObjective):
    def __init__(self, dungeon: str):
        self.dungeon = dungeon

    def is_completed(self, player_data: Dict[str, Any]) -> bool:
        return player_data.get(f"complete_{self.dungeon}", False)

# Base Quest class
class Quest(ABC):
    def __init__(self, quest_id: int, name: str, description: str, rewards: Dict[str, Any]):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.rewards = rewards
        self.completed = False

    @abstractmethod
    def check_completion(self, player_data: Dict[str, Any]) -> bool:
        pass

    def complete(self, player_data: Dict[str, Any]):
        if self.check_completion(player_data):
            self.completed = True
            self.give_rewards(player_data)
            return True
        return False

    def give_rewards(self, player_data: Dict[str, Any]):
        for key, value in self.rewards.items():
            player_data.setdefault(key, 0)
            player_data[key] += value

# MMORPG Quest with objectives
class MMORPGQuestWithObjectives(Quest):
    def __init__(self, quest_id: int, name: str, description: str, rewards: Dict[str, Any], objectives: List[QuestObjective]):
        super().__init__(quest_id, name, description, rewards)
        self.objectives = objectives

    def check_completion(self, player_data: Dict[str, Any]) -> bool:
        return all(obj.is_completed(player_data) for obj in self.objectives)

# MMORPG-style Quest
class MMORPGQuest(Quest):
    def __init__(self, quest_id: int, name: str, description: str, rewards: Dict[str, Any], requirements: Dict[str, int]):
        super().__init__(quest_id, name, description, rewards)
        self.requirements = requirements

    def check_completion(self, player_data: Dict[str, Any]) -> bool:
        for req, amount in self.requirements.items():
            if player_data.get(req, 0) < amount:
                return False
        return True

# Generate 300 MMORPG quests
def generate_mmorpg_quests(start_id=1, count=300):
    quests = []
    for i in range(count):
        qid = start_id + i
        name = f"MMORPG Quest {qid}"
        desc = f"Complete MMORPG objective {qid}"
        rewards = {
            "gold": random.randint(100, 1000),
            "xp": random.randint(50, 500),
            "item": f"item_{random.randint(1, 50)}"
        }
        requirements = {
            f"kill_monster_{random.randint(1, 20)}": random.randint(5, 50),
            f"collect_item_{random.randint(1, 10)}": random.randint(1, 10),
            f"explore_area_{random.randint(1, 15)}": random.randint(1, 3),
            f"complete_dungeon_{random.randint(1, 5)}": random.randint(1, 2)
        }
        quests.append(MMORPGQuest(qid, name, desc, rewards, requirements))
    return quests

# Example usage for 300 MMORPG quests
if __name__ == "__main__":
    mmorpg_quests = generate_mmorpg_quests()
    print(f"Generated {len(mmorpg_quests)} MMORPG quests.")
    # Print first 3 quests for demonstration
    for quest in mmorpg_quests[:3]:
        print(vars(quest))
