from typing import Dict, Optional

# mountSystem.py

class Mount:
    def __init__(self, mount_id: int, name: str, speed: float, stamina: int):
        self.mount_id = mount_id
        self.name = name
        self.speed = speed
        self.stamina = stamina
        self.is_summoned = False

    def summon(self):
        if not self.is_summoned:
            self.is_summoned = True
            print(f"{self.name} has been summoned.")
        else:
            print(f"{self.name} is already summoned.")

    def dismiss(self):
        if self.is_summoned:
            self.is_summoned = False
            print(f"{self.name} has been dismissed.")
        else:
            print(f"{self.name} is not summoned.")

    def __repr__(self):
        return f"<Mount {self.name} (Speed: {self.speed}, Stamina: {self.stamina})>"

class Horse(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Swift Horse", speed=1.5, stamina=100)

class Dragon(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Fire Dragon", speed=3.0, stamina=300)

class Wolf(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Shadow Wolf", speed=2.0, stamina=120)

class Tiger(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Saber Tiger", speed=2.2, stamina=140)

class Elephant(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "War Elephant", speed=1.0, stamina=400)

class Griffin(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Sky Griffin", speed=2.8, stamina=250)

class Unicorn(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Mystic Unicorn", speed=2.5, stamina=180)

class Camel(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Desert Camel", speed=1.2, stamina=200)

class Bear(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Mountain Bear", speed=1.3, stamina=220)

class Panther(Mount):
    def __init__(self, mount_id: int):
        super().__init__(mount_id, "Night Panther", speed=2.4, stamina=130)

# Example mount data for easy reference
mount_data = [
    {"class": Horse, "id": 1},
    {"class": Dragon, "id": 2},
    {"class": Wolf, "id": 3},
    {"class": Tiger, "id": 4},
    {"class": Elephant, "id": 5},
    {"class": Griffin, "id": 6},
    {"class": Unicorn, "id": 7},
    {"class": Camel, "id": 8},
    {"class": Bear, "id": 9},
    {"class": Panther, "id": 10},
]
# Additional methods for Mounts

def get_mount_by_id(mount_id: int) -> Optional[Mount]:
    """Return a new instance of a mount class by its id."""
    for entry in mount_data:
        if entry["id"] == mount_id:
            return entry["class"](mount_id)
    return None

def get_all_mounts() -> Dict[int, Mount]:
    """Return a dictionary of all available mount instances keyed by id."""
    return {entry["id"]: entry["class"](entry["id"]) for entry in mount_data}
class PlayerMounts:
    def __init__(self):
        self.mounts: Dict[int, Mount] = {}
        self.active_mount: Optional[Mount] = None

    def add_mount(self, mount: Mount):
        self.mounts[mount.mount_id] = mount
        print(f"Mount {mount.name} added to collection.")

    def summon_mount(self, mount_id: int):
        if self.active_mount:
            self.active_mount.dismiss()
            self.active_mount = None
        mount = self.mounts.get(mount_id)
        if mount:
            mount.summon()
            self.active_mount = mount
        else:
            print("Mount not found.")

    def dismiss_active_mount(self):
        if self.active_mount:
            self.active_mount.dismiss()
            self.active_mount = None
        else:
            print("No active mount to dismiss.")

    def list_mounts(self):
        for mount in self.mounts.values():
            print(mount)

# Example usage:
if __name__ == "__main__":
    player_mounts = PlayerMounts()
    horse = Mount(1, "Swift Horse", 1.5, 100)
    dragon = Mount(2, "Fire Dragon", 3.0, 300)

    player_mounts.add_mount(horse)
    player_mounts.add_mount(dragon)

    player_mounts.list_mounts()
    player_mounts.summon_mount(1)
    player_mounts.summon_mount(2)
    player_mounts.dismiss_active_mount()