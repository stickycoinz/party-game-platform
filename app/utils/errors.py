from fastapi import HTTPException
from typing import Optional

def lobby_not_found_error(lobby_name: str) -> HTTPException:
    """404 error for missing lobby."""
    return HTTPException(
        status_code=404, 
        detail=f"Lobby '{lobby_name}' not found"
    )

def player_not_found_error(player_name: str) -> HTTPException:
    """404 error for missing player."""
    return HTTPException(
        status_code=404, 
        detail=f"Player '{player_name}' not found"
    )

def lobby_already_exists_error(lobby_name: str) -> HTTPException:
    """400 error for duplicate lobby."""
    return HTTPException(
        status_code=400, 
        detail=f"Lobby '{lobby_name}' already exists"
    )

def player_already_in_lobby_error(player_name: str) -> HTTPException:
    """400 error for duplicate player in lobby."""
    return HTTPException(
        status_code=400, 
        detail=f"Player '{player_name}' already in lobby"
    )

def not_enough_players_error(min_players: int) -> HTTPException:
    """409 error for insufficient players."""
    return HTTPException(
        status_code=409, 
        detail=f"Not enough players. Minimum {min_players} required"
    )

def players_not_ready_error() -> HTTPException:
    """409 error when not all players are ready."""
    return HTTPException(
        status_code=409, 
        detail="Not all players are ready"
    )

def invalid_name_error(name: str) -> HTTPException:
    """400 error for invalid name."""
    return HTTPException(
        status_code=400, 
        detail=f"Invalid name: '{name}'"
    )

def host_only_action_error() -> HTTPException:
    """403 error for host-only actions."""
    return HTTPException(
        status_code=403, 
        detail="Only the host can perform this action"
    )

def game_already_started_error() -> HTTPException:
    """409 error when game is already in progress."""
    return HTTPException(
        status_code=409, 
        detail="Game already in progress"
    )
