import asyncio
import time
import random
from typing import Dict, List
from app.schemas.game import (
    TapGauntletData, BuzzerTriviaData, GameState, GameType, GameResults, PlayerScore,
    WSEvent, WSEventType, TapAction, TapResponseAction, VoteCategoryAction, BuzzerAction, 
    AwardPointsAction, NextQuestionAction, EndGameAction
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

# ===== BUZZER TRIVIA GAME =====

# Trivia Categories
TRIVIA_CATEGORIES = [
    "Movies & TV",
    "Sports",
    "Science",
    "History",
    "Food & Drink",
    "Music",
    "Geography",
    "Animals"
]

# Trivia Questions Bank
TRIVIA_QUESTIONS = {
    "Movies & TV": [
        {"question": "What movie features the line 'May the Force be with you'?", "answer": "Star Wars"},
        {"question": "Which TV show features a chemistry teacher turned meth cook?", "answer": "Breaking Bad"},
        {"question": "Who directed the movie 'Jaws'?", "answer": "Steven Spielberg"},
    ],
    "Sports": [
        {"question": "How many players are on a basketball team on the court at once?", "answer": "5"},
        {"question": "What sport is played at Wimbledon?", "answer": "Tennis"},
        {"question": "Which country won the 2018 FIFA World Cup?", "answer": "France"},
    ],
    "Science": [
        {"question": "What is the chemical symbol for gold?", "answer": "Au"},
        {"question": "How many bones are in an adult human body?", "answer": "206"},
        {"question": "What planet is known as the Red Planet?", "answer": "Mars"},
    ],
    "History": [
        {"question": "In which year did World War II end?", "answer": "1945"},
        {"question": "Who was the first person to walk on the moon?", "answer": "Neil Armstrong"},
        {"question": "Which ancient wonder was located in Alexandria?", "answer": "Lighthouse of Alexandria"},
    ],
    "Food & Drink": [
        {"question": "What spice is derived from the Crocus flower?", "answer": "Saffron"},
        {"question": "Which country is famous for inventing pizza?", "answer": "Italy"},
        {"question": "What is the main ingredient in guacamole?", "answer": "Avocado"},
    ],
    "Music": [
        {"question": "Which instrument has 88 keys?", "answer": "Piano"},
        {"question": "Who composed 'The Four Seasons'?", "answer": "Vivaldi"},
        {"question": "What does 'forte' mean in music?", "answer": "Loud"},
    ],
    "Geography": [
        {"question": "What is the capital of Australia?", "answer": "Canberra"},
        {"question": "Which river is the longest in the world?", "answer": "Nile"},
        {"question": "How many continents are there?", "answer": "7"},
    ],
    "Animals": [
        {"question": "What is the largest mammal in the world?", "answer": "Blue Whale"},
        {"question": "How many hearts does an octopus have?", "answer": "3"},
        {"question": "What is a group of lions called?", "answer": "Pride"},
    ]
}

async def start_buzzer_trivia(lobby_name: str, lobby: Lobby, manager) -> bool:
    """Start a Buzzer Trivia game."""
    if lobby.game_state != GameState.WAITING:
        return False

    # Pick 3 random categories for voting
    selected_categories = random.sample(TRIVIA_CATEGORIES, 3)

    # Initialize game data
    game_data = BuzzerTriviaData(
        state=GameState.STARTING,
        start_time=time.time(),
        category_options=selected_categories,
        total_scores={player.name: 0 for player in lobby.players}
    )

    lobby.current_game = game_data
    lobby.game_state = GameState.STARTING

    storage = await get_storage()
    await storage.set_lobby(lobby_name, lobby)

    # Broadcast game start
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STARTED,
        payload={
            "game_type": GameType.BUZZER_TRIVIA,
            "message": "🔔 Buzzer Trivia! First, vote for a category!",
            "countdown": 3
        },
        timestamp=time.time()
    ))

    # Start game loop
    asyncio.create_task(_run_buzzer_trivia_game(lobby_name, manager))
    return True

async def _run_buzzer_trivia_game(lobby_name: str, manager):
    """Run the Buzzer Trivia game loop."""
    # Simple 3 second countdown
    for i in range(3, 0, -1):
        await manager.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.TICK,
            payload={"countdown": i, "message": f"Starting in {i}..."},
            timestamp=time.time()
        ))
        await asyncio.sleep(1)

    # Start category voting
    await _start_category_voting(lobby_name, manager)

async def _start_category_voting(lobby_name: str, manager):
    """Start the category voting phase."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)

    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return

    game_data = lobby.current_game

    # Show category voting
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "phase": "category_voting",
            "categories": game_data.category_options,
            "message": "Vote for a trivia category!",
            "time_limit": 15
        },
        timestamp=time.time()
    ))

    # Wait 15 seconds for voting
    await asyncio.sleep(15)

    # Determine winning category
    await _select_winning_category(lobby_name, manager)

async def _select_winning_category(lobby_name: str, manager):
    """Select the winning category and start the trivia round."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return
    
    game_data = lobby.current_game
    
    # Count votes
    vote_counts = {}
    for voted_category in game_data.category_votes.values():
        vote_counts[voted_category] = vote_counts.get(voted_category, 0) + 1
    
    # Select winning category (most votes, or random if tie)
    if vote_counts:
        max_votes = max(vote_counts.values())
        winners = [cat for cat, votes in vote_counts.items() if votes == max_votes]
        game_data.selected_category = random.choice(winners)
    else:
        # No votes, pick random
        game_data.selected_category = random.choice(game_data.category_options)
    
    # Pick a random question from the winning category
    questions = TRIVIA_QUESTIONS.get(game_data.selected_category, [])
    if questions:
        selected_q = random.choice(questions)
        game_data.current_question = selected_q["question"]
        game_data.correct_answer = selected_q["answer"]
    
    await storage.set_lobby(lobby_name, lobby)
    
    # Show the category result and start the buzzer round
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "phase": "category_result",
            "selected_category": game_data.selected_category,
            "message": f"📊 Category chosen: {game_data.selected_category}",
        },
        timestamp=time.time()
    ))
    
    await asyncio.sleep(3)  # Show category for 3 seconds
    
    # Start the buzzer round
    await _start_buzzer_round(lobby_name, manager)

async def _start_buzzer_round(lobby_name: str, manager):
    """Start the buzzer round with the trivia question."""
    try:
        storage = await get_storage()
        lobby = await storage.get_lobby(lobby_name)
        
        if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
            print(f"Invalid lobby or game data for {lobby_name}")
            return
        
        game_data = lobby.current_game
        game_data.buzzers = []  # Reset buzzers for this round
        
        await storage.set_lobby(lobby_name, lobby)
        
        # Show the trivia question
        await manager.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.GAME_STATE,
            payload={
                "phase": "buzzer_question",
                "round": game_data.current_round,
                "category": game_data.selected_category,
                "question": game_data.current_question,
                "message": f"Round {game_data.current_round}: Get ready to buzz in!",
            },
            timestamp=time.time()
        ))
        
        # Wait 3 seconds for players to read the question
        await asyncio.sleep(3)
        
        # Activate buzzers with countdown
        buzzer_timeout = 20  # 20 seconds for buzzing
        await manager.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.GAME_STATE,
            payload={
                "phase": "buzzer_active",
                "message": "🔔 BUZZERS ACTIVE! First to buzz gets to answer!",
                "countdown_seconds": buzzer_timeout
            },
            timestamp=time.time()
        ))
        
        # Countdown with live updates
        start_time = time.time()
        last_countdown = buzzer_timeout
        
        while time.time() - start_time < buzzer_timeout:
            current_remaining = buzzer_timeout - int(time.time() - start_time)
            
            # Send countdown update when it changes
            if current_remaining != last_countdown and current_remaining >= 0:
                await manager.broadcast_to_lobby(lobby_name, WSEvent(
                    type=WSEventType.GAME_STATE,
                    payload={
                        "phase": "buzzer_countdown",
                        "countdown": current_remaining,
                        "message": f"🔔 {current_remaining}s left to buzz in!" if current_remaining > 0 else "🔔 Time's up!",
                        "keep_buzzing": True
                    },
                    timestamp=time.time()
                ))
                last_countdown = current_remaining
            
            # Check if someone buzzed - but don't end immediately, keep accepting buzzers
            lobby = await storage.get_lobby(lobby_name)
            if lobby and isinstance(lobby.current_game, BuzzerTriviaData):
                game_data = lobby.current_game
                # Just update live buzzer list, don't end the phase
                if game_data.buzzers:
                    await manager.broadcast_to_lobby(lobby_name, WSEvent(
                        type=WSEventType.GAME_STATE,
                        payload={
                            "phase": "live_buzzers",
                            "buzzer_player": game_data.buzzers[-1]["player"],  # Most recent buzzer
                            "buzzers": game_data.buzzers,
                            "message": f"🔔 {len(game_data.buzzers)} player(s) buzzed in! {current_remaining}s remaining",
                            "keep_buzzing": True,
                            "countdown": current_remaining
                        },
                        timestamp=time.time()
                    ))
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        # Time's up! Now show final buzzer results
        lobby = await storage.get_lobby(lobby_name)
        if lobby and isinstance(lobby.current_game, BuzzerTriviaData):
            game_data = lobby.current_game
            if game_data.buzzers:
                await _show_buzzer_order(lobby_name, manager)
                return
        
        # Timeout - no one buzzed
        await manager.broadcast_to_lobby(lobby_name, WSEvent(
            type=WSEventType.GAME_STATE,
            payload={
                "phase": "timeout",
                "message": f"⏰ Time's up! The answer was: {game_data.correct_answer}",
            },
            timestamp=time.time()
        ))
        
        await asyncio.sleep(3)
        
        # End round or continue to next question
        await _end_buzzer_round(lobby_name, manager)
        
    except Exception as e:
        print(f"Error in _start_buzzer_round: {e}")
        await _end_buzzer_trivia_game(lobby_name, manager)

async def _show_buzzer_order(lobby_name: str, manager):
    """Show buzzer order and wait for host to award points."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return
    
    game_data = lobby.current_game
    
    # Sort buzzers by time (earliest first)
    game_data.buzzers.sort(key=lambda x: x["time"])
    
    # Assign positions
    for i, buzzer in enumerate(game_data.buzzers):
        buzzer["position"] = i + 1
    
    await storage.set_lobby(lobby_name, lobby)
    
    # Show buzzer order to everyone, answer only to host
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "phase": "host_judging",
            "question": game_data.current_question,
            "buzzers": game_data.buzzers,
            "message": f"🔔 Waiting for host to award points...",
            "show_answer_to_host_only": True
        },
        timestamp=time.time()
    ))
    
    # Send answer separately to host only
    host_player = lobby.host
    await manager.send_to_player(lobby_name, host_player, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "phase": "host_answer",
            "correct_answer": game_data.correct_answer,
            "host_controls": True,
            "message": f"🎯 ANSWER: {game_data.correct_answer}"
        },
        timestamp=time.time()
    ))
    
    # Don't auto-advance - wait for host action

async def _end_buzzer_round(lobby_name: str, manager):
    """End the current round and either start next question or end game."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return
    
    game_data = lobby.current_game
    
    # Check if we should continue or end the game
    if game_data.current_round >= game_data.max_rounds:
        await _end_buzzer_trivia_game(lobby_name, manager)
    else:
        # Start next round
        game_data.current_round += 1
        await _start_next_question(lobby_name, manager)

async def _start_next_question(lobby_name: str, manager):
    """Start the next trivia question."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return
    
    game_data = lobby.current_game
    
    # Pick a new question from the same category
    questions = TRIVIA_QUESTIONS.get(game_data.selected_category, [])
    if questions:
        selected_q = random.choice(questions)
        game_data.current_question = selected_q["question"]
        game_data.correct_answer = selected_q["answer"]
    
    # Reset buzzers for new round
    game_data.buzzers = []
    
    await storage.set_lobby(lobby_name, lobby)
    
    # Show new question
    await manager.broadcast_to_lobby(lobby_name, WSEvent(
        type=WSEventType.GAME_STATE,
        payload={
            "phase": "next_question",
            "round": game_data.current_round,
            "message": f"Round {game_data.current_round} coming up!",
        },
        timestamp=time.time()
    ))
    
    await asyncio.sleep(2)
    
    # Start the new buzzer round
    await _start_buzzer_round(lobby_name, manager)

async def _end_buzzer_trivia_game(lobby_name: str, manager):
    """End the buzzer trivia game and show final results."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return
    
    game_data = lobby.current_game
    game_data.state = GameState.FINISHED
    game_data.end_time = time.time()
    
    # Calculate final scores based on host-awarded points (no auto-scoring)
    scores = []
    for player in lobby.players:
        score = game_data.total_scores.get(player.name, 0)  # Only host-awarded points
        scores.append(PlayerScore(
            player_name=player.name,
            score=score,
            position=0
        ))
    
    # Sort by score descending
    scores.sort(key=lambda x: x.score, reverse=True)
    for i, score in enumerate(scores):
        score.position = i + 1
    
    # Determine winner
    winner = scores[0].player_name if scores and scores[0].score > 0 else None
    
    results = GameResults(
        game_type=GameType.BUZZER_TRIVIA,
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

async def handle_buzzer_trivia_action(lobby_name: str, player_name: str, action: str, payload: dict, manager):
    """Handle Buzzer Trivia specific actions."""
    storage = await get_storage()
    lobby = await storage.get_lobby(lobby_name)
    
    if not lobby or not isinstance(lobby.current_game, BuzzerTriviaData):
        return
    
    game_data = lobby.current_game
    
    if action == "vote_category":
        category = payload.get("category")
        if category and category in game_data.category_options:
            game_data.category_votes[player_name] = category
            await storage.set_lobby(lobby_name, lobby)
            
            # Confirm vote
            await manager.send_to_player(lobby_name, player_name, WSEvent(
                type=WSEventType.GAME_STATE,
                payload={"category_vote_confirmed": True, "voted_category": category},
                timestamp=time.time()
            ))
    
    elif action == "buzz":
        buzz_time = payload.get("timestamp", time.time())
        
        # Check if player already buzzed
        player_already_buzzed = any(b["player"] == player_name for b in game_data.buzzers)
        if not player_already_buzzed:
            game_data.buzzers.append({
                "player": player_name,
                "time": buzz_time,
                "position": 0  # Will be calculated later
            })
            
            await storage.set_lobby(lobby_name, lobby)
            
            # Confirm buzz
            await manager.send_to_player(lobby_name, player_name, WSEvent(
                type=WSEventType.GAME_STATE,
                payload={"buzz_confirmed": True},
                timestamp=time.time()
            ))
            
            # Broadcast live buzzer update to everyone
            await manager.broadcast_to_lobby(lobby_name, WSEvent(
                type=WSEventType.GAME_STATE,
                payload={
                    "phase": "live_buzzers",
                    "buzzer_player": player_name,
                    "buzzers": game_data.buzzers,
                    "message": f"🔔 {player_name} buzzed in! (#{len(game_data.buzzers)})",
                    "keep_buzzing": True  # Keep buzzers active
                },
                timestamp=time.time()
            ))
    
    elif action == "award_points":
        awarded_player = payload.get("player_name")
        points = payload.get("points", 1)
        
        if awarded_player and awarded_player in [p.name for p in lobby.players]:
            # Award points
            game_data.total_scores[awarded_player] = game_data.total_scores.get(awarded_player, 0) + points
            await storage.set_lobby(lobby_name, lobby)
            
            # Broadcast point award
            await manager.broadcast_to_lobby(lobby_name, WSEvent(
                type=WSEventType.GAME_STATE,
                payload={
                    "phase": "points_awarded",
                    "awarded_player": awarded_player,
                    "points": points,
                    "message": f"🏆 {awarded_player} gets {points} point{'s' if points != 1 else ''}!",
                    "total_scores": game_data.total_scores
                },
                timestamp=time.time()
            ))
    
    elif action == "next_question":
        # Only the host can trigger next question
        if player_name == lobby.host:
            await asyncio.sleep(2)  # Brief pause before next question
            await _start_next_question(lobby_name, manager)
    
    elif action == "end_game":
        # Only the host can end the game
        if player_name == lobby.host:
            await _end_buzzer_trivia_game(lobby_name, manager)
