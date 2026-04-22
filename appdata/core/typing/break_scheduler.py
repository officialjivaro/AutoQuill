# File: appdata/core/typing/break_scheduler.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, Tuple, Union

# Public types
Token = Tuple[str, Union[str, None]]  # ("CHAR", "a") or ("KEY", "ENTER")


@dataclass
class BreakConfig:
    """
    Configuration for human-like pauses.

    - enabled: master toggle.
    - word_min/word_max: inclusive range for number of "word units" between pauses.
    - sec_min/sec_max: inclusive range (uniform) for pause duration in seconds.
    """
    enabled: bool = False
    word_min: int = 18
    word_max: int = 42
    sec_min: float = 2.0
    sec_max: float = 5.0

    # Hard caps to guard extreme UI inputs; tune as needed.
    _MAX_WORDS_CAP: int = 500
    _MAX_SECS_CAP: float = 60.0

    def sanitize(self) -> None:
        """Clamp and normalize values to safe, coherent ranges."""
        # Coerce to ints/floats and handle swapped ranges.
        self.word_min = max(1, int(self.word_min))
        self.word_max = max(1, int(self.word_max))
        if self.word_min > self.word_max:
            self.word_min, self.word_max = self.word_max, self.word_min

        self.sec_min = max(0.0, float(self.sec_min))
        self.sec_max = max(0.0, float(self.sec_max))
        if self.sec_min > self.sec_max:
            self.sec_min, self.sec_max = self.sec_max, self.sec_min

        # Caps
        self.word_min = min(self.word_min, self._MAX_WORDS_CAP)
        self.word_max = min(self.word_max, self._MAX_WORDS_CAP)
        self.sec_min = min(self.sec_min, self._MAX_SECS_CAP)
        self.sec_max = min(self.sec_max, self._MAX_SECS_CAP)


class BreakScheduler:
    """
    Counts "word units" during typing and signals when to pause.

    Rules implemented (per Build Plan):
      - A "word unit" increments when a **word is completed** by a boundary
        (whitespace or specific punctuation), and **each [KEY] token counts as 1**
        and also acts as a boundary.
      - Pauses are only triggered **after finishing a word**, never mid-word.
      - When a loop wait occurs, call `reset_after_loop()` so "loop wins" and the
        break counter resets as if a break occurred.

    Usage pattern for engine integration:
        scheduler = BreakScheduler(BreakConfig(enabled=True, ...))
        for kind, payload in instructions:
            pause_secs = scheduler.step(kind, payload)
            if pause_secs is not None:
                time.sleep(pause_secs)
            # ... perform actual injection for this token ...
        # On loop wait:
        scheduler.reset_after_loop()
    """

    # Punctuation that should act as **word-completing** boundaries.
    _BOUNDARY_PUNCT = {".", ",", "!", "?", ":", ";", ")", "]"}

    def __init__(self, config: Optional[BreakConfig] = None, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._config = config or BreakConfig()
        self._config.sanitize()

        # Runtime state
        self._in_word: bool = False          # True if we are currently inside a word
        self._units_since_break: int = 0     # Count since last pause (or reset)
        self._next_target: Optional[int] = None  # Next unit threshold to trigger pause

        self._refresh_target()

    # ----------------- Public API -----------------

    @property
    def config(self) -> BreakConfig:
        return self._config

    def update_config(self, config: BreakConfig) -> None:
        """Replace configuration and reset internal counters/targets."""
        self._config = config
        self._config.sanitize()
        self.reset_state()

    def reset_state(self) -> None:
        """Reset runtime state; use when starting a new typing session."""
        self._in_word = False
        self._units_since_break = 0
        self._refresh_target()

    def reset_after_loop(self) -> None:
        """
        Called when the engine performs a loop wait.
        Implements "loop wins": treat as if a break occurred and reset counters.
        """
        if not self._config.enabled:
            return
        self._in_word = False
        self._units_since_break = 0
        self._refresh_target()

    def step(self, kind: str, payload: Optional[str]) -> Optional[float]:
        """
        Consume one token and return pause seconds if a break is due; else None.

        Parameters:
            kind: "CHAR" or "KEY"
            payload: character for "CHAR", or key-name for "KEY" (ignored for counting except as boundary/unit).

        Behavior:
          - For CHAR:
                - If it is a boundary char and we were inside a word, we *complete* that word (units += 1).
                - If it is not a boundary, we mark that we are inside a word.
          - For KEY:
                - If we were in a word, first complete that word (units += 1).
                - Then count the KEY itself as one unit (units += 1).
                - KEY is a boundary (we are not in a word after it).

        Returns:
            float seconds to pause (uniform in [sec_min, sec_max]) if threshold reached *after* completing a word,
            otherwise None.
        """
        if not self._config.enabled or self._next_target is None:
            return None

        if kind == "CHAR":
            ch = payload or ""
            if self._is_boundary_char(ch):
                # We only increment if a word actually preceded the boundary.
                if self._in_word:
                    self._increment_units()  # completed word
                    self._in_word = False
                    return self._maybe_pause()
                else:
                    # Boundary after boundary: still not in a word.
                    self._in_word = False
                    return None
            else:
                # Non-boundary character -> we are inside a word.
                self._in_word = True
                return None

        elif kind == "KEY":
            # KEY tokens are boundaries and also count as a unit.
            if self._in_word:
                # Finalize the preceding word first.
                self._increment_units()
                maybe = self._maybe_pause()
                # Even if a pause just triggered on the word completion, we still count the KEY unit.
                # This keeps semantics consistent with acceptance example ("world" and then "[ENTER]").
                self._in_word = False
                self._increment_units()
                # If the word completion already triggered a pause, prefer that signal (pause happens after the word).
                # Otherwise, see if the KEY unit itself hits the target.
                return maybe if maybe is not None else self._maybe_pause()
            else:
                # No word in progress; KEY itself counts as a unit and acts as boundary.
                self._in_word = False
                self._increment_units()
                return self._maybe_pause()

        # Unknown token kinds are ignored for counting.
        return None

    # ----------------- Internals -----------------

    def _is_boundary_char(self, ch: str) -> bool:
        """Whitespace or listed punctuation counts as a word-completing boundary."""
        return (ch.isspace()) or (ch in self._BOUNDARY_PUNCT)

    def _increment_units(self) -> None:
        self._units_since_break += 1

    def _refresh_target(self) -> None:
        if self._config.enabled:
            self._next_target = self._rng.randint(self._config.word_min, self._config.word_max)
        else:
            self._next_target = None

    def _maybe_pause(self) -> Optional[float]:
        """If we've reached/exceeded the target, choose a pause and reset counters/target."""
        if self._next_target is None:
            return None
        if self._units_since_break >= self._next_target:
            # Choose pause duration and reset for next cycle.
            pause_secs = self._rng.uniform(self._config.sec_min, self._config.sec_max)
            self._units_since_break = 0
            self._refresh_target()
            # After a pause, we are not in a word.
            self._in_word = False
            # Clamp to non-negative.
            return max(0.0, float(pause_secs))
        return None
