# Первичные источники, проверенные 2026-10-04

- https://docs.python.org/3/library/tkinter.html — Tkinter/Tk availability,
  optional module preflight and cooperative UI/event-thread requirements.
- https://docs.python.org/3/using/windows.html — Windows Python installation
  guidance; actual runtime/host version must be recorded on target device.
- https://docs.python.org/3/library/subprocess.html — explicit argv, pipe I/O,
  timeout/termination behavior. Buffered output has memory implications.

Предложение Tkinter основано на existing prototype/Python backend и этих docs;
это engineering inference для minimal pilot, не measured winner среди shells.
Other packaging candidates can be evaluated under DEC5-01 after device receipt.
No documentation reference proves runtime installed/working on the user's PC.
