
from dataclasses import dataclass
@dataclass
class Clock:
    t: int = 0
    def step(self, dt: int = 1): self.t += dt
