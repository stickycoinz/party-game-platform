from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from typing import Dict, Set
import json
import asyncio
import time
from app.schemas.game import WSEvent, WSEventType, GameState
from app.schemas.lobby import Lobby, Player
from app.utils.storage import get_storage
from app.utils.errors import lobby_not_found_error

router = APIRouter()

# Connection management
class ConnectionManager:
    def __init__(self):
        # lobby_name -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> (lobby_name, player_name)
        self.connection_info: Dict[WebSocket, tuple[str, str]] = {}
    
    async def connect(self, websocket: WebSocket, lobby_name: str, player_name: str):
        await websocket.accept()
        
        if lobby_name not in self.active_connections:
            self.active_connections[lobby_name] = set()
        
        self.active_connections[lobby_name].add(websocket)
        self.connection_info[websocket] = (lobby_name, player_name)
        
        # Notify others that player joined
        await self.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.PLAYER_JOINED,
            payload={"player_name": player_name},
            timestamp=time.time()
        ), exclude=websocket)
    
    async def disconnect(self, websocket: WebSocket):
        if websocket in self.connection_info:
            lobby_name, player_name = self.connection_info[websocket]
            
            # Remove from connections
            if lobby_name in self.active_connections:
                self.active_connections[lobby_name].discard(websocket)
                if not self.active_connections[lobby_name]:
                    del self.active_connections[lobby_name]
            
            del self.connection_info[websocket]
            
            # Remove player from lobby data
            storage = await get_storage()
            lobby = await storage.get_lobby(lobby_name)
            if lobby:
                # Remove the player from the lobby
                lobby.players = [p for p in lobby.players if p.name != player_name]
                
                # If the leaving player was the host, assign new host
                if lobby.host == player_name and lobby.players:
                    lobby.host = lobby.players[0].name
                    print(f"Host changed to {lobby.host} after {player_name} left")
                
                await storage.set_lobby(lobby_name, lobby)
                
                # Notify others that player left with updated lobby
                await self.broadcast_to_lobby(lobby_name, WSEvent(
                    type=WSEventType.PLAYER_LEFT,
                    payload={"player_name": player_name},
                    timestamp=time.time()
                ))
                
                # Send updated lobby state
                await self.broadcast_to_lobby(lobby_name, WSEvent(
                    type=WSEventType.LOBBY_UPDATED,
                    payload={"lobby": lobby.model_dump()},
                    timestamp=time.time()
                ))
            
            # Clean up empty lobbies
            await self._cleanup_empty_lobby(lobby_name)
    
    async def broadcast_to_lobby(self, lobby_name: str, event: WSEvent, exclude: WebSocket = None):
        if lobby_name not in self.active_connections:
            return
        
        message = event.model_dump_json()
        connections_to_remove = []
        
        for websocket in self.active_connections[lobby_name]:
            if exclude and websocket == exclude:
                continue
            
            try:
                await websocket.send_text(message)
            except Exception:
                connections_to_remove.append(websocket)
        
        # Remove dead connections
        for websocket in connections_to_remove:
            await self.disconnect(websocket)
    
    async def send_to_player(self, lobby_name: str, player_name: str, event: WSEvent):
        if lobby_name not in self.active_connections:
            return
        
        message = event.model_dump_json()
        for websocket in self.active_connections[lobby_name]:
            if websocket in self.connection_info:
                _, ws_player_name = self.connection_info[websocket]
                if ws_player_name == player_name:
                    try:
                        await websocket.send_text(message)
                    except Exception:
                        await self.disconnect(websocket)
                    break
    
    async def _cleanup_empty_lobby(self, lobby_name: str):
        """Remove lobby if no connections remain."""
        if lobby_name not in self.active_connections or not self.active_connections[lobby_name]:
            storage = await get_storage()
            await storage.delete_lobby(lobby_name)

# Global connection manager
manager = ConnectionManager()

@router.websocket("/ws/lobby/{lobby_name}")
async def websocket_endpoint(websocket: WebSocket, lobby_name: str, player_name: str):
    storage = await get_storage()
    
    # Verify lobby exists
    lobby = await storage.get_lobby(lobby_name)
    if not lobby:
        await websocket.close(code=4004, reason="Lobby not found")
        return
    
    # Verify player is in lobby
    player_in_lobby = any(p.name == player_name for p in lobby.players)
    if not player_in_lobby:
        await websocket.close(code=4009, reason="Player not in lobby")
        return
    
    await manager.connect(websocket, lobby_name, player_name)
    
    try:
        # Send initial lobby state
        await websocket.send_text(WSEvent(
            type=WSEventType.LOBBY_UPDATED,
            payload={
                "lobby": lobby.model_dump(),
                "connected_players": [
                    info[1] for info in manager.connection_info.values() 
                    if info[0] == lobby_name
                ]
            },
            timestamp=time.time()
        ).model_dump_json())
        
        while True:
            data = await websocket.receive_text()
            await handle_websocket_message(websocket, lobby_name, player_name, data)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)

async def handle_websocket_message(websocket: WebSocket, lobby_name: str, player_name: str, data: str):
    """Handle incoming WebSocket messages."""
    try:
        message = json.loads(data)
        event_type = message.get("type")
        payload = message.get("payload", {})
        
        storage = await get_storage()
        lobby = await storage.get_lobby(lobby_name)
        if not lobby:
            await websocket.send_text(WSEvent(
                type=WSEventType.ERROR,
                payload={"error": "Lobby not found"},
                timestamp=time.time()
            ).model_dump_json())
            return
        
        if event_type == WSEventType.PLAYER_READY:
            await handle_player_ready(lobby_name, player_name, True)
        
        elif event_type == WSEventType.PLAYER_UNREADY:
            await handle_player_ready(lobby_name, player_name, False)
        
        elif event_type == WSEventType.CHAT:
            message_text = payload.get("message", "")
            if message_text.strip():
                await manager.broadcast_to_lobby(lobby_name, WSEvent(
                    type=WSEventType.CHAT_MESSAGE,
                    payload={
                        "player_name": player_name,
                        "message": message_text,
                    },
                    timestamp=time.time()
                ))
        
        elif event_type == WSEventType.GAME_ACTION:
            await handle_game_action(lobby_name, player_name, payload)
        
        elif event_type == WSEventType.PING:
            await websocket.send_text(WSEvent(
                type=WSEventType.PONG,
                payload={"timestamp": time.time()},
                timestamp=time.time()
            ).model_dump_json())
        
    except json.JSONDecodeError:
        await websocket.send_text(WSEvent(
            type=WSEventType.ERROR,
            payload={"error": "Invalid JSON"},
            timestamp=time.time()
        ).model_dump_json())
    except Exception as e:
        await websocket.send_text(WSEvent(
            type=WSEventType.ERROR,
            payload={"error": str(e)},
            timestamp=time.time()
        ).model_dump_json())

async def cleanup_stale_connections():
    """Clean up connections that might have failed to disconnect properly."""
    storage = await get_storage()
    all_lobbies = await storage.get_all_lobbies()
    
    for lobby_name, lobby in all_lobbies.items():
        if lobby_name in manager.active_connections:
            # Get connected player names
            connected_players = {
                info[1] for info in manager.connection_info.values() 
                if info[0] == lobby_name
            }
            
            # Remove players who are in lobby but not connected
            original_count = len(lobby.players)
            lobby.players = [p for p in lobby.players if p.name in connected_players]
            
            if len(lobby.players) != original_count:
                print(f"Cleaned up {original_count - len(lobby.players)} stale players from {lobby_name}")
                await storage.set_lobby(lobby_name, lobby)
                
                # Broadcast updated lobby
                await manager.broadcast_to_lobby(lobby_name, WSEvent(
                    type=WSEventType.LOBBY_UPDATED,
                    payload={"lobby": lobby.model_dump()},
                    timestamp=time.time()
                ))

async def handle_player_ready(lobby_name: str, player_name: str, is_ready: bool):
    """Handle player ready/unready state changes."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    if not lobby:
        return
    
    # Update player ready state
    for player in lobby.players:
        if player.name == player_name:
            player.is_ready = is_ready
            break
    
    await storage.set_lobby(lobby_name, lobby)
    
    # Broadcast lobby update
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.LOBBY_UPDATED,
        payload={"lobby": lobby.model_dump()},
        timestamp=time.time()
    ))

async def handle_game_action(lobby_name: str, player_name: str, payload: dict):
    """Handle game-specific actions."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    if not lobby or not lobby.current_game:
        return
    
    action = payload.get("action")
    
    # Import game logic here to avoid circular imports
    if lobby.current_game.game_type == "tap_gauntlet":
        from app.routers.game_logic import handle_tap_gauntlet_action
        await handle_tap_gauntlet_action(lobby_name, player_name, action, payload, manager)
    elif lobby.current_game.game_type == "reverse_trivia":
        from app.routers.game_logic import handle_reverse_trivia_action
        await handle_reverse_trivia_action(lobby_name, player_name, action, payload, manager)

# Utility function to broadcast lobby updates
async def broadcast_lobby_update(lobby_name: str):
    """Broadcast lobby state to all connected clients."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    if lobby:
        await manager.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.LOBBY_UPDATED,
            payload={"lobby": lobby.model_dump()},
            timestamp=time.time()
        ))

# Export manager for use in other modules
__all__ = ["router", "manager", "broadcast_lobby_update"]
