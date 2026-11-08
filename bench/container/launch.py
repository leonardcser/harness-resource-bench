"""Mark the exec of the agent for startup timing. Setup time does not count."""

import os
import sys
import termios
import time

if os.isatty(0):
    attributes = termios.tcgetattr(0)
    attributes[3] &= ~(termios.ECHO | termios.ECHONL)
    termios.tcsetattr(0, termios.TCSANOW, attributes)
os.write(1, f"\x1b]777;BENCH_LAUNCH={time.monotonic_ns()}\x07".encode())
os.execvp(sys.argv[1], sys.argv[1:])
