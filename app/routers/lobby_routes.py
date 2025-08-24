from fastapi import APIRouter, HTTPException, Depends
from typing import List
import secrets
from app.schemas.lobby import LobbyCreate, LobbyJoin, Lobby, Player, LobbyInfo
from app.schemas.game import StartGameRequest, GameType, GameState
from app.utils.storage import get_storage, StorageBackend
from app.utils.errors import *
from app.utils.ids import validate_name, generate_player_id
from app.routers.game_logic import start_tap_gauntlet, start_buzzer_trivia

router = APIRouter(prefix="/lobby", tags=["lobby"])

@router.post("/create", response_model=Lobby)
async def create_lobby(data: LobbyCreate, storage: StorageBackend = Depends(get_storage)) -> Lobby:
    """Create a new lobby."""
    # Validate inputs
    if not validate_name(data.lobby_name):
        raise invalid_name_error(data.lobby_name)
    if not validate_name(data.player_name):
        raise invalid_name_error(data.player_name)
    
    # Check if lobby already exists
    existing_lobby = await storage.get_lobby(data.lobby_name)
    if existing_lobby:
        raise lobby_already_exists_error(data.lobby_name)
    
    # Create host token
    host_token = secrets.token_urlsafe(16)
    
    # Create lobby
    lobby = Lobby(
        lobby_name=data.lobby_name,
        host=data.player_name,
        players=[Player(
            name=data.player_name, 
            is_ready=False,
            player_id=generate_player_id()
        )],
        host_token=host_token
    )
    
    await storage.set_lobby(data.lobby_name, lobby)
    return lobby

@router.post("/join", response_model=Lobby)
async def join_lobby(data: LobbyJoin, storage: StorageBackend = Depends(get_storage)) -> Lobby:
    """Join an existing lobby."""
    # Validate inputs
    if not validate_name(data.player_name):
        raise invalid_name_error(data.player_name)
    
    lobby = await storage.get_lobby(data.lobby_name)
    if not lobby:
        raise lobby_not_found_error(data.lobby_name)
    
    # Check if player already in lobby
    if any(p.name == data.player_name for p in lobby.players):
        raise player_already_in_lobby_error(data.player_name)
    
    # Check lobby capacity
    if len(lobby.players) >= 12:
        raise HTTPException(status_code=409, detail="Lobby is full")
    
    # Check if game is in progress
    if lobby.game_state == GameState.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Game is in progress")
    
    # Add player
    lobby.players.append(Player(
        name=data.player_name, 
        is_ready=False,
        player_id=generate_player_id()
    ))
    
    await storage.set_lobby(data.lobby_name, lobby)
    return lobby

@router.post("/{lobby_name}/ready", response_model=Lobby)
async def ready_up(lobby_name: str, player_name: str, storage: StorageBackend = Depends(get_storage)) -> Lobby:
    """Toggle player ready state."""
    lobby = await storage.get_lobby(lobby_name)
    if not lobby:
        raise lobby_not_found_error(lobby_name)
    
    # Find player and toggle ready state
    player_found = False
    for player in lobby.players:
        if player.name == player_name:
            player.is_ready = not player.is_ready
            player_found = True
            break
    
    if not player_found:
        raise player_not_found_error(player_name)
    
    await storage.set_lobby(lobby_name, lobby)
    return lobby

@router.post("/{lobby_name}/start")
async def start_game(
    lobby_name: str, 
    data: StartGameRequest,
    storage: StorageBackend = Depends(get_storage)
) -> dict:
    """Start a game in the lobby."""
    lobby = await storage.get_lobby(lobby_name)
    if not lobby:
        raise lobby_not_found_error(lobby_name)
    
    # Verify host token (if provided)
    if data.host_token and data.host_token != lobby.host_token:
        raise host_only_action_error()
    
    # Check minimum players
    if len(lobby.players) < 2:
        raise not_enough_players_error(2)
    
    # Check all players are ready
    if not all(player.is_ready for player in lobby.players):
        raise players_not_ready_error()
    
    # Check game not already started
    if lobby.game_state != GameState.WAITING:
        raise game_already_started_error()
    
    # Start the specific game type
    success = False
    from app.routers.ws_routes import manager
    
    try:
        if data.game_type == GameType.TAP_GAUNTLET:
            success = await start_tap_gauntlet(lobby_name, lobby, manager)
        elif data.game_type == GameType.BUZZER_TRIVIA:
            success = await start_buzzer_trivia(lobby_name, lobby, manager)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown game type: {data.game_type}")
            
    except Exception as e:
        print(f"Error starting {data.game_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting game: {str(e)}")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start game")
    
    return {"ok": True, "game_type": data.game_type}

@router.get("/{lobby_name}", response_model=Lobby)
async def get_lobby(lobby_name: str, storage: StorageBackend = Depends(get_storage)) -> Lobby:
    """Get lobby information."""
    lobby = await storage.get_lobby(lobby_name)
    if not lobby:
        raise lobby_not_found_error(lobby_name)
    return lobby

@router.get("/", response_model=List[LobbyInfo])
async def list_lobbies(storage: StorageBackend = Depends(get_storage)) -> List[LobbyInfo]:
    """List all active lobbies."""
    all_lobbies = await storage.get_all_lobbies()
    return [
        LobbyInfo(
            lobby_name=lobby.lobby_name,
            player_count=len(lobby.players),
            game_state=lobby.game_state,
            current_game_type=lobby.current_game.game_type if lobby.current_game else None
        )
        for lobby in all_lobbies.values()
    ]

@router.delete("/{lobby_name}")
async def delete_lobby(
    lobby_name: str, 
    host_token: str,
    storage: StorageBackend = Depends(get_storage)
) -> dict:
    """Delete a lobby (host only)."""
    lobby = await storage.get_lobby(lobby_name)
    if not lobby:
        raise lobby_not_found_error(lobby_name)
    
    if host_token != lobby.host_token:
        raise host_only_action_error()
    
    await storage.delete_lobby(lobby_name)
    return {"ok": True}
