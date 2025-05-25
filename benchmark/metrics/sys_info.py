import os
import platform
import re
from typing import Dict, Union


def get_system_info() -> Dict[str, Union[str, int, float]]:
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'os_release': platform.release(),
        'os_distro': get_linux_distro()
    }

    cpu_info = get_cpu_info()
    info.update(cpu_info)

    mem_info = get_memory_info()
    info.update(mem_info)

    info['hostname'] = platform.node()
    info['architecture'] = platform.machine()

    return info


def get_linux_distro() -> str:
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    return line.split('=')[1].strip().strip('"')
    except FileNotFoundError:
        return platform.platform()
    return "Unknown Linux"


def get_cpu_info() -> Dict[str, Union[str, int]]:
    cpu_info = {}

    try:
        cpu_info['cpu_cores'] = os.cpu_count()

        with open('/proc/cpuinfo') as f:
            cpuinfo = f.read()

        model_match = re.search(r'model name\s*:\s*(.*)', cpuinfo)
        if model_match:
            cpu_info['cpu_model'] = model_match.group(1).strip()

        freq_match = re.search(r'cpu MHz\s*:\s*(.*)', cpuinfo)
        if freq_match:
            cpu_info['cpu_frequency_mhz'] = float(freq_match.group(1).strip())

    except Exception as e:
        print(f"Error getting CPU info: {e}")

    return cpu_info


def get_memory_info() -> Dict[str, Union[str, int, float]]:
    mem_info = {}

    try:
        with open('/proc/meminfo') as f:
            meminfo = f.read()

        total_match = re.search(r'MemTotal:\s*(\d+) kB', meminfo)
        if total_match:
            mem_info['memory_total_gb'] = int(total_match.group(1)) / 1024 / 1024

        free_match = re.search(r'MemAvailable:\s*(\d+) kB', meminfo)
        if free_match:
            mem_info['memory_available_gb'] = int(free_match.group(1)) / 1024 / 1024

    except Exception as e:
        print(f"Error getting memory info: {e}")

    return mem_info


def print_system_info(info: Dict[str, Union[str, int, float]]):
    """Выводит информацию о системе в удобном формате"""
    print("\n=== Системная информация ===")
    print(f"ОС: {info['os_distro']}")
    print(f"Версия ядра: {info['os_release']}")
    print(f"Архитектура: {info['architecture']}")
    print(f"Имя хоста: {info['hostname']}")

    print("\n=== Процессор ===")
    print(f"Модель: {info.get('cpu_model', 'N/A')}")
    print(f"Ядер: {info.get('cpu_cores', 'N/A')}")
    print(f"Частота: {info.get('cpu_frequency_mhz', 'N/A')} MHz")

    print("\n=== Память ===")
    print(f"Всего: {info.get('memory_total_gb', 'N/A'):.2f} GB")
    print(f"Доступно: {info.get('memory_available_gb', 'N/A'):.2f} GB")

    print("\n=== Диски ===")
    for mount, disk in info.get('disks', {}).items():
        print(f"{mount}: {disk['used']} used of {disk['total']} ({disk['use_percent']})")


if __name__ == "__main__":
    system_info = get_system_info()
    print_system_info(system_info)
