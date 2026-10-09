"""Omega Prime agent loop. Hermes turn phases, adapted, with none of the TUI or gateway chrome."""

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.runtime import OmegaPrimeAgent

__all__ = ["Agent", "OmegaPrimeAgent", "run_conversation"]
