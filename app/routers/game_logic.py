import asyncio
import time
import random
from typing import Dict, List
from app.schemas.game import (
    TapGauntletData, GameState, GameType, GameResults, PlayerScore,
    WSEvent, WSEventType, TapAction, TapResponseAction
)
from app.schemas.lobby import Lobby
from app.utils.storage import get_storage

async def start_tap_gauntlet(lobby_name: str, lobby: Lobby, manager) -> bool:
    """Start a Tap Gauntlet game."""
    if lobby.game_state != GameState.WAITING:
        return False
    
    # Initialize game data
    game_data = TapGauntletData(
        state=GameState.STARTING,
        start_time=time.time(),
        player_taps={player.name: 0 for player in lobby.players},
        last_tap_times={player.name: 0 for player in lobby.players},
        server_prompts={player.name: [] for player in lobby.players}
    )
    
    lobby.current_game = game_data
    lobby.game_state = GameState.STARTING
    
    storage = await get_storage()
    await storage.set_lobby(lobby_name, lobby)
    
    # Broadcast game start
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STARTED,
        payload={
            "game_type": GameType.TAP_GAUNTLET,
            "duration": game_data.duration_seconds,
            "countdown": 3
        },
        timestamp=time.time()
    ))
    
    # Start countdown and game loop
    asyncio.create_task(_run_tap_gauntlet_game(lobby_name, manager))
    return True

async def _run_tap_gauntlet_game(lobby_name: str, manager):
    """Run the Tap Gauntlet game loop."""
    storage = await get_storage()
    
    # 3-second countdown
    for i in range(3, 0, -1):
        await manager.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.TICK,
            payload={"countdown": i, "message": f"Starting in {i}..."},
            timestamp=time.time()
        ))
        await asyncio.sleep(1)
    
    # Start game
    lobby = await storage.get_lobby(lobby_name)
    if not lobby or not isinstance(lobby.current_game, TapGauntletData):
        return
    
    game_data = lobby.current_game
    game_data.state = GameState.IN_PROGRESS
    game_data.start_time = time.time()
    lobby.game_state = GameState.IN_PROGRESS
    
    await storage.set_lobby(lobby_name, lobby)
    
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "state": "in_progress",
            "message": "TAP NOW!",
            "game_time": 0,
            "remaining_time": game_data.duration_seconds
        },
        timestamp=time.time()
    ))
    
    # Game loop with anti-cheat prompts
    game_duration = game_data.duration_seconds
    tick_interval = 0.5  # Send updates every 500ms
    anti_cheat_interval = 2.0  # Send validation prompts every 2 seconds
    
    start_time = time.time()
    last_anti_cheat = start_time
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        remaining = max(0, game_duration - elapsed)
        
        if remaining <= 0:
            break
        
        # Send anti-cheat prompts
        if current_time - last_anti_cheat >= anti_cheat_interval:
            await _send_anti_cheat_prompts(lobby_name, manager)
            last_anti_cheat = current_time
        
        # Send tick update
        lobby = await storage.get_lobby(lobby_name)
        if lobby and isinstance(lobby.current_game, TapGauntletData):
            await manager.broadcast_to_lobby(lobby_name, WSEvent(
                type=WSEventType.TICK,
                payload={
                    "game_time": elapsed,
                    "remaining_time": remaining,
                    "scores": lobby.current_game.player_taps
                },
                timestamp=current_time
            ))
        
        await asyncio.sleep(tick_interval)
    
    # End game
    await _end_tap_gauntlet_game(lobby_name, manager)

async def _send_anti_cheat_prompts(lobby_name: str, manager):
    """Send random prompts to players for anti-cheat validation."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, TapGauntletData):
        return
    
    game_data = lobby.current_game
    prompt_id = str(random.randint(1000, 9999))
    current_time = time.time()
    
    # Randomly select 1-2 players for validation
    players_to_prompt = random.sample(
        [p.name for p in lobby.players], 
        min(2, len(lobby.players))
    )
    
    for player_name in players_to_prompt:
        if player_name not in game_data.server_prompts:
            game_data.server_prompts[player_name] = []
        game_data.server_prompts[player_name].append(current_time)
        
        await manager.send_to_player(lobby_name, player_name, WSEvent(
            type=WSEventType.GAME_STATE,
            payload={
                "anti_cheat_prompt": prompt_id,
                "timestamp": current_time
            },
            timestamp=current_time
        ))
    
    await storage.set_lobby(lobby_name, lobby)

async def _end_tap_gauntlet_game(lobby_name: str, manager):
    """End the Tap Gauntlet game and calculate results."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, TapGauntletData):
        return
    
    game_data = lobby.current_game
    game_data.state = GameState.FINISHED
    game_data.end_time = time.time()
    
    # Calculate results
    scores = []
    for player in lobby.players:
        taps = game_data.player_taps.get(player.name, 0)
        scores.append(PlayerScore(
            player_name=player.name,
            score=taps,
            position=0  # Will be set after sorting
        ))
    
    # Sort by score descending
    scores.sort(key=lambda x: x.score, reverse=True)
    for i, score in enumerate(scores):
        score.position = i + 1
    
    # Determine winner
    winner = scores[0].player_name if scores else None
    
    results = GameResults(
        game_type=GameType.TAP_GAUNTLET,
        winner=winner,
        scores=scores,
        duration_seconds=game_data.end_time - game_data.start_time
    )
    
    # Reset lobby state
    lobby.game_state = GameState.WAITING
    lobby.current_game = None
    
    # Reset player ready states
    for player in lobby.players:
        player.is_ready = False
    
    await storage.set_lobby(lobby_name, lobby)
    
    # Broadcast results
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_FINISHED,
        payload={"results": results.model_dump()},
        timestamp=time.time()
    ))

async def handle_tap_gauntlet_action(lobby_name: str, player_name: str, action: str, payload: dict, manager):
    """Handle Tap Gauntlet specific actions."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, TapGauntletData):
        return
    
    game_data = lobby.current_game
    
    if game_data.state != GameState.IN_PROGRESS:
        return
    
    current_time = time.time()
    
    if action == "tap":
        await _handle_tap_action(lobby_name, player_name, current_time, manager)
    elif action == "tap_response":
        prompt_id = payload.get("prompt_id")
        await _handle_tap_response(lobby_name, player_name, prompt_id, current_time, manager)

async def _handle_tap_action(lobby_name: str, player_name: str, tap_time: float, manager):
    """Handle a tap action with anti-cheat validation."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, TapGauntletData):
        return
    
    game_data = lobby.current_game
    
    # Anti-cheat: Check tap rate
    last_tap = game_data.last_tap_times.get(player_name, 0)
    time_since_last = tap_time - last_tap
    
    if time_since_last < (1.0 / game_data.max_taps_per_second):
        # Rate limit exceeded, ignore tap
        return
    
    # Update tap count and timestamp
    game_data.player_taps[player_name] = game_data.player_taps.get(player_name, 0) + 1
    game_data.last_tap_times[player_name] = tap_time
    
    await storage.set_lobby(lobby_name, lobby)
    
    # Send immediate feedback to player
    await manager.send_to_player(lobby_name, player_name, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "tap_confirmed": True,
            "current_taps": game_data.player_taps[player_name]
        },
        timestamp=tap_time
    ))

async def _handle_tap_response(lobby_name: str, player_name: str, prompt_id: str, response_time: float, manager):
    """Handle anti-cheat prompt response."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, TapGauntletData):
        return
    
    game_data = lobby.current_game
    
    # Validate response timing (should be quick for legitimate players)
    player_prompts = game_data.server_prompts.get(player_name, [])
    
    # Find the most recent prompt within reasonable time window
    valid_response = False
    for prompt_time in reversed(player_prompts):
        if response_time - prompt_time < 2.0:  # 2 second window
            valid_response = True
            break
    
    if not valid_response:
        # Potential cheating - could reduce tap count or flag player
        # For now, we'll just log it
        print(f"Suspicious activity from {player_name}: invalid prompt response")
    
    await storage.set_lobby(lobby_name, lobby)
