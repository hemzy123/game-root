# 🎮 Multi-Genre Game Engine

A custom game project combining FPS, MOBA, and MMORPG elements. This project is structured for modular expansion and supports multiple gameplay modes, networking, matchmaking, and AI systems. All code is implemented in Python, and assets are organized by type and purpose.

---

## 📂 Project Structure Overview

game-root/
├── assets/                 # Models, textures, sounds, animations, effects
├── backend/                # Player data, matchmaking logic, server logs, authentication, purchases
├── characters/             # Categorized character types: players, heroes, enemies, NPCs
├── configs/                # JSON configuration files for weapons, maps, heroes, UI, and server
├── core/                   # Game loop, time management, events, AI manager, resource loading
├── fps/                    # FPS game mechanics: shooting, aiming, damage, loot, UI, modes
├── moba/                   # MOBA gameplay systems: hero control, map logic, roles, UI
├── mmorpg/                 # MMORPG systems: quests, classes, mounts, inventory, skills
├── multiplayer/            # Session, party, guild, lobby, and friend systems
├── matchmaking/            # Match rules, queue logic, and matchmaker core
├── networking/             # WebSocket handling, server sync, anti-cheat, encryption, chat
├── maps/                   # Level/map data for FPS, MOBA, and MMORPG modes
├── physics/                # Physics logic (currently empty)
├── scripts/                # Utility scripts: input, camera, bots, analytics, replays
├── ui/                     # UI elements for all modes, including main menu and HUDs
├── main.py                 # Main entry point for initializing the game

---

## 🚀 Features

- Fully modular codebase split by genre and functionality
- Real-time networking, anti-cheat, and encrypted data flow
- Dynamic matchmaking and party/lobby system
- AI-controlled bots and NPCs for PvE and PvP modes
- Config-driven systems for easy balancing and updates
- Separated UI layers for FPS, MOBA, and MMORPG interfaces

---

## 📄 License

This project is currently **not licensed**.  
All rights are reserved by the developer.  
To publish, distribute, or contribute, please apply an appropriate license or contact the author.

---

## 👤 Author

**Henry Onabiyi**  
📍 St. John’s, Newfoundland and Labrador  

## 🛠️ To-Do (Optional)

- [ ] Implement physics engine components
- [ ] Add test coverage for all major modules
- [ ] Integrate login/auth UI flow
- [ ] Add client-side settings for video/audio

---

> For questions or suggestions, feel free to reach out by email.
