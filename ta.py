from math import floor, ceil
from time import time

#>>>
class ThroughputAdvice:
  def __init__(self, now, window, interval):
    """Construct throughput advice, given a starting time `now`,
       a duration over which to enforce `window`, and
       an `interval` size that the window is evenly divided into."""

    self.interval = interval
    self.count = floor(window / interval)
    assert self.count == ceil(window / interval)

    self.total = 0
    self.state = [0] * self.count
    self.advice = float('Infinity')
    self.last_advice = t - window

    self.index = self.index_of(now)
    self.next_update = self.next_time(now)

  def index_of(self, t):
    return floor(t / self.interval) % self.count

  def next_time(self, t):
    return (floor(t / self.interval) + 1) * self.interval

  def update_time(self, t):
    if t < self.next_update:
      return
    assert t + self.interval > self.next_update,\
      "time has gone backwards"

    new_index = self.index_of(t)
    if t >= self.next_update + (self.interval * self.count):
      self.total = 0
      self.state = [0] * nbuckets
    else:
      while True:
        self.index = (self.index + 1) % self.count
        self.total = self.total - self.state[self.index]
        self.state[self.index] = 0
        if self.index == new_index:
          break

    assert sum(self.state) == self.total
    self.index = new_index
    self.next_update = self.next_time(t)

  def set_advice(self, t, advice):
    """Update the throughput advice based on a received signal."""

    if advice < self.advice:
      self.state = [0] * self.count
      self.total = 0
    elif self.advice_updated + self.interval * self.count > t:
      # Ignore increases too soon after an update.
      # This could be smarter about increases, but this is safe.
      return
    self.advice = advice
    self.advice_updated = t

  def data_sent(self, t, amount):
    """Record that at time `t`, data of length `amount` was sent."""

    self.update_time(t)
    self.state[self.index] = self.state[self.index] + amount
    self.total = self.total + amount

  def is_within_advice(self, t, amount):
    """Test whether at time `t`, data of length `amount`
       is within the provided throughput advice."""

    self.update_time(t)
    return self.total + amount <= self.advice
#<<<

  def __repr__(self):
    return f"""ThroughputAdvice {self.advice}@{self.last_advice}
               {self.interval}*{self.count}[{self.index}] = {self.total} [{",".join([str(x) for x in self.state])}]"""

if __name__ == "__main__":
  def fill(t, ta):
    # Over 10 seconds, send 100*1000k
    for i in [x * 0.1 for x in range(0, 100)]:
      ta.data_sent(t + i, 1000)

  t = time()
  ta = ThroughputAdvice(t, 60, 1)
  ta.set_advice(t, 100_000)
  fill(t, ta)

  # 100k limit is hit
  assert not ta.is_within_advice(t + 20, 1000)
  # Out to 55 seconds, even with an update
  ta.set_advice(t + 55, 110_000)
  assert not ta.is_within_advice(t + 55, 1000)
  # It opens up again at 60
  assert ta.is_within_advice(t + 60, 1000)

  t = t + 60
  fill(t, ta)

  # OK, filled up again
  assert not ta.is_within_advice(t + 20, 1000)
  # Expanding advice makes room for more
  ta.set_advice(t, 110_000)
  assert ta.is_within_advice(t + 20, 1000)
  # So does shrinking, because it clears state
  ta.set_advice(t, 90_000)
  assert ta.is_within_advice(t + 20, 1000)
