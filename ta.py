from math import floor, ceil
from time import time

#>>>
class ThroughputAdvice:
  def __init__(self, role, now, window, interval):
    """Construct throughput advice,
       given a role `role` ("sender" or "network"),
       starting time `now`,
       a duration over which to enforce `window` (in seconds), and
       an `interval` size that the window is evenly divided into."""

    assert role == "sender" or role == "network"
    self.role = role
    self.interval = interval
    self.count = floor(window / interval)
    assert self.count == ceil(window / interval)

    self.total = 0
    self.state = [0] * self.count
    self.advice = float('Infinity')
    self.last_advice = now - window - interval

    self.index = self.index_of(now)
    self.next_index_time = self.next_time(now)

    self.next_advice = None

  def index_of(self, t):
    return floor(t / self.interval) % self.count

  def next_time(self, t):
    return (floor(t / self.interval) + 1) * self.interval

  def expired(self, t):
    return t > self.last_advice + (self.interval * self.count)

  def _advance_time(self, t):
    if self.next_advice is not None:
      self.next_advice._advance_time(t)
      if self.next_advice.expired(t):
        self.next_advice = None
      elif self.expired(t):
        self.total = self.next_advice.total
        self.state = self.next_advice.state
        self.advice = self.next_advice.advice
        self.last_advice = self.next_advice.last_advice
        self.next_advice = self.next_advice.next_advice

    if t < self.next_index_time: return
    assert t + self.interval > self.next_index_time,\
      "time has gone backwards"

    new_index = self.index_of(t)
    if t >= self.next_index_time + (self.interval * self.count):
      self.total = 0
      self.state = [0] * nbuckets
    else:
      while self.index != new_index:
        self.index = (self.index + 1) % self.count
        self.total = self.total - self.state[self.index]
        self.state[self.index] = 0

    assert sum(self.state) == self.total
    self.index = new_index
    self.next_index_time = self.next_time(t)

  def set_advice(self, t, advice):
    """Update the throughput advice based on a received signal."""

    self._advance_time(t)

    if self.expired(t) or advice == self.advice:
      self.advice = advice
      self.last_advice = t
      return

    if self.next_advice is None:
      window = self.count * self.interval
      self.next_advice = \
        ThroughputAdvice(self.role, t, window, self.interval)

    self.next_advice.set_advice(t, advice)

  def _record(self, t, amount):
    self.state[self.index] = self.state[self.index] + amount
    self.total = self.total + amount
    if self.next_advice is not None:
      self.next_advice._record(t, amount)

  def data_sent(self, t, amount):
    """Record that at time `t`, data of length `amount` was sent."""

    self._advance_time(t)
    self._record(t, amount)

  def _is_ok(self, t, amount):
    is_ok = self.total + amount <= self.advice
    if self.next_advice is None:
      return is_ok
    next_ok = self.next_advice._is_ok(t, amount)
    if self.role == "sender":
      # Senders follow all active advice.
      return is_ok and next_ok
    # Network monitoring allows the most lenient advice.
    return is_ok or next_ok

  def is_within_advice(self, t, amount):
    """Test whether at time `t`, data of length `amount`
       is within the provided throughput advice."""

    self._advance_time(t)
    return self.expired(t) or self._is_ok(t, amount)
#<<<

  def __repr__(self):
    r = f"""ThroughputAdvice {self.role} {self.advice}@{self.last_advice}
  {self.interval}*{self.count}[{self.index}] = {self.total} [{",".join([str(x) for x in self.state])}]"""
    if self.next_advice is not None:
      r = r + "\n  next " + repr(self.next_advice)
    return r

if __name__ == "__main__":
  def fill(t, ta):
    # Over 10 seconds, send 100*1000k
    for i in [x * 0.1 for x in range(0, 100)]:
      ta.data_sent(t + i, 1000)

  t = time()
  ta = ThroughputAdvice("sender", t, 60, 1)
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

  # Filled up again, but the advice at t=55 applies
  # now that the original advice has expired.
  assert ta.is_within_advice(t + 20, 1000)
  assert ta.advice == 110_000,f"{repr(ta)}"

  # Shrinking works, because that creates fresh state
  ta.set_advice(t, 90_000)
  assert ta.is_within_advice(t + 20, 1000)
