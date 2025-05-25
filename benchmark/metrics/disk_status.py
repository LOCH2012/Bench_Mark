import os
import re
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
import time
import subprocess


def get_physical_disk(mountpoint: str) -> Optional[str]:
    source = subprocess.run(
        ["findmnt", "-n", "-o", "SOURCE", mountpoint],
        capture_output=True, text=True
    ).stdout.strip()

    if not source:
        return None

    if source.startswith("/dev/sd") or source.startswith("/dev/nvme"):
        disk = re.sub(r'\d+$', '', source.split('/')[-1])  # sdb1 → sdb
        return disk

    if source.startswith("/dev/mapper"):
        pvs = subprocess.run(
            ["pvs", "--noheadings", "-o", "PV_NAME"],
            capture_output=True, text=True
        ).stdout.strip()
        if pvs:
            disk = re.sub(r'\d+$', '', pvs.split('/')[-1])
            return disk

    if "zfs" in subprocess.run(["mount"], capture_output=True, text=True).stdout:
        pool = source.split('/')[-1]
        zpool_status = subprocess.run(
            ["zpool", "status", pool, "-LP"],
            capture_output=True, text=True
        ).stdout
        disks = re.findall(r'/dev/(sd[a-z]+|nvme\d+n\d+)', zpool_status)
        if disks:
            return disks[0]

    if "btrfs" in subprocess.run(["mount"], capture_output=True, text=True).stdout:
        btrfs_info = subprocess.run(
            ["btrfs", "filesystem", "show", mountpoint],
            capture_output=True, text=True
        ).stdout
        disks = re.findall(r'/dev/(sd[a-z]+|nvme\d+n\d+)', btrfs_info)
        if disks:
            return disks[0]

    return None


class DiskStats(NamedTuple):
    major: int
    minor: int
    name: str
    read_complete: int
    read_merged: int
    read_sectors: int
    read_ms: int
    write_complete: int
    write_merged: int
    write_sectors: int
    write_ms: int
    io_pending: int
    io_ms: int
    io_queue_ms: int

    def compare(self, other, interval: float = 1.0) -> Dict[str, float]:
        delta_read = other.read_complete - self.read_complete
        delta_write = other.write_complete - self.write_complete
        delta_read_ms = other.read_ms - self.read_ms
        delta_write_ms = other.write_ms - self.write_ms
        delta_io_ms = other.io_ms - self.io_ms

        total_ms = interval * 1000
        read_util = delta_read_ms / total_ms * 100
        write_util = delta_write_ms / total_ms * 100
        total_util = delta_io_ms / total_ms * 100

        return {
            'read_iops': delta_read / interval,
            'write_iops': delta_write / interval,
            'read_throughput': (other.read_sectors - self.read_sectors) * 512 / interval,
            'write_throughput': (other.write_sectors - self.write_sectors) * 512 / interval,
            'read_utilization': read_util,
            'write_utilization': write_util,
            'total_utilization': total_util,
            'queue_length': other.io_pending
        }


def get_diskstats(disk_name: str) -> Optional[DiskStats]:
    try:
        with open('/proc/diskstats') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 14 or parts[2] != disk_name:
                    continue

                return DiskStats(
                    major=int(parts[0]),
                    minor=int(parts[1]),
                    name=parts[2],
                    read_complete=int(parts[3]),
                    read_merged=int(parts[4]),
                    read_sectors=int(parts[5]),
                    read_ms=int(parts[6]),
                    write_complete=int(parts[7]),
                    write_merged=int(parts[8]),
                    write_sectors=int(parts[9]),
                    write_ms=int(parts[10]),
                    io_pending=int(parts[11]),
                    io_ms=int(parts[12]),
                    io_queue_ms=int(parts[13])
                )
    except Exception as e:
        print(f"Error reading /proc/diskstats: {e}")
    return None


def get_disk_io_utilization(disk: str, interval: float = 1.0):
    if not disk:
        return

    s1 = get_diskstats(disk)
    while s1:
        time.sleep(interval)
        s2 = get_diskstats(disk)
        stats = s1.compare(s2, interval)
        s1 = s2
        print(f"\nДиск: {disk}")
        print(f"  IOPS (чтение): {stats['read_iops']:.1f}/s")
        print(f"  IOPS (запись): {stats['write_iops']:.1f}/s")
        print(f"  Пропускная способность (чтение): {stats['read_throughput'] / 1024 / 1024:.1f} MB/s")
        print(f"  Пропускная способность (запись): {stats['write_throughput'] / 1024 / 1024:.1f} MB/s")
        print(f"  Утилизация (чтение): {stats['read_utilization']:.1f}%")
        print(f"  Утилизация (запись): {stats['write_utilization']:.1f}%")
        print(f"  Общая утилизация: {stats['total_utilization']:.1f}%")
        print(f"  Длина очереди: {stats['queue_length']}")


if __name__ == "__main__":
    print("Измеряем утилизацию дисков...")
    disk = get_physical_disk("/storage")
    get_disk_io_utilization(disk)
