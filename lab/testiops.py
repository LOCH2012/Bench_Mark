import os
import time
import random

def measure_iops(
    file_path,
    block_size=4 * 1024,  # 4K для классического теста
    total_size=160 * 2**20,  # Сколько операций выполнить
    mode="randwrite",  # randwrite / randread
    direct_io=True,   # Прямой ввод-вывод (O_DIRECT)
    repeats=1,
):
    total_ops = total_size // block_size
    # Готовим файл (если нужно)
    if mode == "randwrite" and not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.truncate(total_size)  # Файл достаточного размера

    # Открываем файл с O_DIRECT (если поддерживается)
    if direct_io and os.name == "posix":
        flags = os.O_RDWR | getattr(os, "O_DIRECT", 0)
        fd = os.open(file_path, flags)
        f = os.fdopen(fd, "rb+" if mode == "randwrite" else "rb", buffering=0)
    else:
        f = open(file_path, "rb+" if mode == "randwrite" else "rb", buffering=0)

    # Готовим случайные смещения
    file_size = os.path.getsize(file_path)
    max_offset = (file_size // block_size) - 1
    offsets = [random.randint(0, max_offset) * block_size for _ in range(total_ops)]

    # Буфер для данных
    data = os.urandom(block_size) if "write" in mode else None

    # Замер времени
    start = time.time()

    for offset in offsets:
        f.seek(offset)
        if "write" in mode:
            f.write(data)
        else:
            f.read(block_size)

    f.close()
    elapsed = time.time() - start

    iops = (total_ops) / elapsed
    print(f"IOPS ({mode}, {block_size}): {iops:.2f}")

if __name__ == "__main__":
    # Примеры запуска
    measure_iops("testfile.bin", mode="randwrite")  # Тест записи
    measure_iops("testfile.bin", mode="randread")   # Тест чтения