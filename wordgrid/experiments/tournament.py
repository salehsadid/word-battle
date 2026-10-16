import time
from typing import List, Dict, Tuple, Optional
from wordgrid.game.engine import GameEngine
from wordgrid.game.rules import GameRules
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.config import GameConfig
from wordgrid.experiments.metrics import MatchResult, AgentTournamentStats


class TournamentRunner:
    """Orchestrates automated tournaments between AI algorithms with alternating starts."""

    def __init__(
        self,
        validator: WordValidatorProtocol,
        config: Optional[GameConfig] = None,
    ):
        self.validator = validator
        self.config = config or GameConfig()
        self.engine = GameEngine(validator=self.validator, config=self.config)

    def play_single_match(
        self,
        agent1: BaseAgent,
        agent2: BaseAgent,
    ) -> MatchResult:
        """Executes a full match between agent1 (as P1) and agent2 (as P2)."""
        state = self.engine.reset(self.config)
        # Both agents simulate with the engine's authoritative rules
        agent1.bind_rules(self.engine.rules)
        agent2.bind_rules(self.engine.rules)
        p1_time = 0.0
        p2_time = 0.0
        p1_moves = 0
        p2_moves = 0
        p1_nodes = 0
        p2_nodes = 0
        p1_cutoffs = 0
        p2_cutoffs = 0
        p1_mcts_sims = 0
        p2_mcts_sims = 0

        match_start = time.perf_counter()

        while not self.engine.is_game_over:
            current_player = self.engine.state.current_player
            current_agent = agent1 if current_player == 1 else agent2

            t0 = time.perf_counter()
            move = current_agent.select_move(self.engine.state, self.validator)
            elapsed = time.perf_counter() - t0

            stats = current_agent.get_last_stats()

            if current_player == 1:
                p1_time += elapsed
                p1_moves += 1
                p1_nodes += stats.get("nodes_visited", 0)
                p1_cutoffs += stats.get("cutoffs", 0)
                p1_mcts_sims += stats.get("simulations", 0)
            else:
                p2_time += elapsed
                p2_moves += 1
                p2_nodes += stats.get("nodes_visited", 0)
                p2_cutoffs += stats.get("cutoffs", 0)
                p2_mcts_sims += stats.get("simulations", 0)

            self.engine.make_move(move)

        duration = time.perf_counter() - match_start
        final_state = self.engine.state

        p1_avg_time = (p1_time / p1_moves) if p1_moves > 0 else 0.0
        p2_avg_time = (p2_time / p2_moves) if p2_moves > 0 else 0.0

        return MatchResult(
            p1_name=agent1.name,
            p2_name=agent2.name,
            p1_score=final_state.scores.get(1, 0),
            p2_score=final_state.scores.get(2, 0),
            winner=final_state.winner,
            total_moves=final_state.move_count,
            duration_seconds=duration,
            p1_avg_time_per_move=p1_avg_time,
            p2_avg_time_per_move=p2_avg_time,
            p1_nodes_visited=p1_nodes,
            p2_nodes_visited=p2_nodes,
            p1_cutoffs=p1_cutoffs,
            p2_cutoffs=p2_cutoffs,
            p1_mcts_sims=p1_mcts_sims,
            p2_mcts_sims=p2_mcts_sims,
            p1_moves=p1_moves,
            p2_moves=p2_moves,
        )

    def run_tournament(
        self,
        agents: List[BaseAgent],
        games_per_pairing: int = 2,
    ) -> Tuple[List[MatchResult], Dict[str, AgentTournamentStats]]:
        """Runs a round-robin tournament across all agent pairs with alternating starts."""
        agent_stats: Dict[str, AgentTournamentStats] = {
            a.name: AgentTournamentStats(name=a.name) for a in agents
        }
        all_matches: List[MatchResult] = []

        n = len(agents)
        for i in range(n):
            for j in range(i + 1, n):
                a1 = agents[i]
                a2 = agents[j]

                for g in range(games_per_pairing):
                    # Alternate starting player
                    if g % 2 == 0:
                        first_agent, second_agent = a1, a2
                    else:
                        first_agent, second_agent = a2, a1

                    result = self.play_single_match(first_agent, second_agent)
                    all_matches.append(result)

                    # Update stats for P1
                    s1 = agent_stats[result.p1_name]
                    s1.matches_played += 1
                    s1.total_score += result.p1_score
                    s1.total_score_diff += (result.p1_score - result.p2_score)
                    s1.total_time_seconds += result.p1_avg_time_per_move * result.p1_moves
                    s1.total_moves += result.p1_moves
                    s1.total_nodes_visited += result.p1_nodes_visited
                    s1.total_cutoffs += result.p1_cutoffs
                    s1.total_mcts_sims += result.p1_mcts_sims

                    if result.winner == 1:
                        s1.wins += 1
                    elif result.winner == 2:
                        s1.losses += 1
                    else:
                        s1.draws += 1

                    # Update stats for P2
                    s2 = agent_stats[result.p2_name]
                    s2.matches_played += 1
                    s2.total_score += result.p2_score
                    s2.total_score_diff += (result.p2_score - result.p1_score)
                    s2.total_time_seconds += result.p2_avg_time_per_move * result.p2_moves
                    s2.total_moves += result.p2_moves
                    s2.total_nodes_visited += result.p2_nodes_visited
                    s2.total_cutoffs += result.p2_cutoffs
                    s2.total_mcts_sims += result.p2_mcts_sims

                    if result.winner == 2:
                        s2.wins += 1
                    elif result.winner == 1:
                        s2.losses += 1
                    else:
                        s2.draws += 1

        return all_matches, agent_stats
