import time
from contextlib import contextmanager


@contextmanager
def timemeasure():
    start_time = time.perf_counter()
    timing = type('Timing', (), {})()
    try:
        yield timing
    finally:
        timing.duration = time.perf_counter() - start_time
        timing.seconds = lambda: timing.duration
        timing.milliseconds = lambda: timing.duration * 1000
        timing.formatted = lambda: f"{timing.duration:.3f} сек"


# print(f"Выполнение заняло: {t.seconds():.3f} секунд")  # Выполнение заняло: 1.500 секунд
# print(f"Или: {t.milliseconds():.1f} мс")  # Или: 1500.0 мс
# print(t.formatted())  # 1.500 сек
