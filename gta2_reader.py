import os
import sys
import glob
import json
import struct
import hashlib
import platform
import subprocess
from datetime import datetime
from pathlib import Path


CACHE_FILE = "gta2_reader_cache.json"
DIAGNOSTIC_FILE = "gta2_reader_diagnostic.json"
MAX_SCAN_DEPTH = 6
MAX_SCAN_SIZE = 200 * 1024 * 1024


def _log(msg):
    print(f"[GTA2Reader] {msg}")


def _load_cache():
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _file_hash(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _read_cstring(data, offset, max_len=32):
    chunk = data[offset:offset + max_len]
    end = chunk.find(b"\x00")
    if end == -1:
        end = max_len
    try:
        return chunk[:end].decode("ascii", errors="ignore")
    except Exception:
        return ""


def _extract_ascii_strings(data, min_len=4, max_count=100, limit_bytes=None):
    result = []
    current = ""
    start = 0
    limit = len(data) if limit_bytes is None else min(len(data), limit_bytes)
    for i in range(limit):
        b = data[i]
        if 32 <= b < 127:
            if not current:
                start = i
            current += chr(b)
        else:
            if len(current) >= min_len:
                result.append((start, current))
                if len(result) >= max_count:
                    return result
            current = ""
    if len(current) >= min_len:
        result.append((start, current))
    return result


def _extract_int32_candidates(data, start=0, end=None, min_val=0, max_val=10_000_000):
    if end is None:
        end = len(data)
    end = min(end, len(data) - 4)
    candidates = []
    for off in range(start, end, 4):
        try:
            val = struct.unpack("<i", data[off:off + 4])[0]
        except struct.error:
            continue
        if min_val <= val <= max_val:
            candidates.append((off, val))
    return candidates


# ============================================================
# ПОИСК ФАЙЛОВ
# ============================================================

def _user_documents():
    home = os.path.expanduser("~")
    docs = os.path.join(home, "Documents")
    if not os.path.isdir(docs):
        docs = os.path.join(home, "Документы")
    if not os.path.isdir(docs):
        docs = home
    return docs


def _candidate_dirs():
    home = os.path.expanduser("~")
    docs = _user_documents()
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", "")
    userprofile = os.environ.get("USERPROFILE", home)

    dirs = [
        # ===== ТВОЙ ПУТЬ (в самом приоритете) =====
        r"C:\Program Files (x86)\GTA 2\Grand Theft Auto 2\player",
        r"C:\Program Files (x86)\GTA 2\Grand Theft Auto 2",
        r"C:\Program Files (x86)\GTA 2",
        r"C:\Program Files\GTA 2\Grand Theft Auto 2\player",
        r"C:\Program Files\GTA 2\Grand Theft Auto 2",
        r"C:\Program Files\GTA 2",

        # ===== Стандартные места =====
        os.path.join(docs, "Rockstar Games", "GTA2", "User Files"),
        os.path.join(docs, "Rockstar Games", "GTA2"),
        os.path.join(docs, "GTA2"),
        os.path.join(docs, "GTA 2"),

        # ===== GOG =====
        r"C:\GOG Games\GTA2\User Files",
        r"C:\GOG Games\GTA2",
        r"C:\GOG Games\GTA 2\Grand Theft Auto 2\player",
        r"C:\GOG Games\GTA 2",

        # ===== Steam =====
        r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto 2",
        r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto 2\player",
        r"C:\SteamLibrary\steamapps\common\Grand Theft Auto 2",
        r"C:\SteamLibrary\steamapps\common\Grand Theft Auto 2\player",
        r"D:\SteamLibrary\steamapps\common\Grand Theft Auto 2",

        # ===== Program Files общие =====
        r"C:\Program Files (x86)\Rockstar Games\GTA2\User Files",
        r"C:\Program Files (x86)\Rockstar Games\GTA2",
        r"C:\Program Files\Rockstar Games\GTA2",
        r"C:\Program Files\Rockstar Games\GTA 2\User Files",
        r"C:\Program Files\Rockstar Games\GTA 2",
        r"C:\Program Files\Rockstar Games\GTA 2\Grand Theft Auto 2\player",

        # ===== Games =====
        r"C:\Games\GTA 2\Grand Theft Auto 2\player",
        r"C:\Games\GTA 2\User Files",
        r"C:\Games\GTA 2",
        r"C:\Games\GTA2",
        r"D:\Games\GTA 2\Grand Theft Auto 2\player",
        r"D:\Games\GTA 2",
        r"D:\Games\GTA2",

        # ===== Корень диска =====
        r"C:\GTA2\player",
        r"C:\GTA2",
        r"C:\GTA 2\Grand Theft Auto 2\player",
        r"C:\GTA 2",
        r"D:\GTA2",
        r"D:\GTA 2\Grand Theft Auto 2\player",

        # ===== Профиль пользователя =====
        os.path.join(userprofile, "GTA2"),
        os.path.join(userprofile, "GTA 2"),

        # ===== AppData =====
        os.path.join(appdata, "GTA2"),
        os.path.join(localappdata, "GTA2"),
    ]

    seen = set()
    result = []
    for d in dirs:
        if not d:
            continue
        normalized = os.path.normpath(d).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(d)
    return result


def _valid_extensions():
    return [
        ".g2s", ".sav", ".gta2", ".sg2", ".dat", ".bin",
        ".save", ".game", ".profile",
    ]


def _looks_like_save_name(name):
    low = name.lower()
    if low.startswith("save") or low.startswith("game"):
        return True
    for ext in _valid_extensions():
        if low.endswith(ext):
            return True
    return False


def scan_known_dirs(verbose=True):
    if verbose:
        _log("Сканирование известных папок...")

    found = []
    for d in _candidate_dirs():
        if not os.path.isdir(d):
            continue
        try:
            for entry in os.listdir(d):
                full = os.path.join(d, entry)
                if os.path.isfile(full) and _looks_like_save_name(entry):
                    size = os.path.getsize(full)
                    if 100 <= size <= MAX_SCAN_SIZE:
                        found.append(full)
                        if verbose:
                            _log(f"  найден: {full} ({size} байт)")
        except (PermissionError, OSError):
            continue

    return found


def scan_drive(root, max_depth=MAX_SCAN_DEPTH, verbose=True):
    if verbose:
        _log(f"Глубокий поиск в {root} (глубина {max_depth})...")

    found = []
    skip = {
        "windows", "programdata", "system volume information", "$recycle.bin",
        "recovery", "perflogs", "msocache", "boot", "intel", "amd", "nvidia",
        "appdata", "node_modules", ".git", "__pycache__", "venv", ".venv",
        "site-packages", "lib", "libs", "temp", "tmp", "cache", ".cache",
        "microsoft", "packages", "installer", "assembly", "winsxs",
    }

    def walk(path, depth):
        if depth > max_depth:
            return
        try:
            entries = os.listdir(path)
        except (PermissionError, OSError):
            return

        for entry in entries:
            low = entry.lower()
            if low in skip:
                continue
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                if "gta" in low or "rockstar" in low:
                    try:
                        for sub in os.listdir(full):
                            sub_full = os.path.join(full, sub)
                            if os.path.isfile(sub_full) and _looks_like_save_name(sub):
                                size = os.path.getsize(sub_full)
                                if 100 <= size <= MAX_SCAN_SIZE:
                                    found.append(sub_full)
                                    if verbose:
                                        _log(f"  найден: {sub_full}")
                            elif os.path.isdir(sub_full):
                                sub_low = sub.lower()
                                if "user" in sub_low or "save" in sub_low or "file" in sub_low:
                                    try:
                                        for f in os.listdir(sub_full):
                                            ff = os.path.join(sub_full, f)
                                            if os.path.isfile(ff) and _looks_like_save_name(f):
                                                size = os.path.getsize(ff)
                                                if 100 <= size <= MAX_SCAN_SIZE:
                                                    found.append(ff)
                                                    if verbose:
                                                        _log(f"  найден: {ff}")
                                    except (PermissionError, OSError):
                                        pass
                    except (PermissionError, OSError):
                        pass
                walk(full, depth + 1)

    walk(root, 0)
    return found


def scan_registry(verbose=True):
    if platform.system() != "Windows":
        return []
    if verbose:
        _log("Проверка реестра Windows...")

    found = []
    try:
        import winreg
    except ImportError:
        return []

    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rockstar Games\GTA2"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rockstar Games\GTA2"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rockstar Games\GTA 2"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rockstar Games\GTA 2"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Rockstar Games\GTA2"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Rockstar Games\GTA 2"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\GTA2"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GTA2"),
    ]

    for root, path in keys:
        try:
            key = winreg.OpenKey(root, path)
        except OSError:
            continue
        try:
            info = winreg.QueryInfoKey(key)
            for i in range(info[1]):
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                except OSError:
                    continue
                if not isinstance(value, str):
                    continue
                if "install" in name.lower() or "path" in name.lower() or "dir" in name.lower():
                    if os.path.isdir(value):
                        if verbose:
                            _log(f"  реестр: {name} = {value}")
                        for sub in ["User Files", "Saves", "Save", ""]:
                            check = os.path.join(value, sub) if sub else value
                            if os.path.isdir(check):
                                try:
                                    for f in os.listdir(check):
                                        ff = os.path.join(check, f)
                                        if os.path.isfile(ff) and _looks_like_save_name(f):
                                            found.append(ff)
                                            if verbose:
                                                _log(f"    найден: {ff}")
                                except (PermissionError, OSError):
                                    pass
        finally:
            winreg.CloseKey(key)

    return found


def scan_gta2_process():
    if platform.system() != "Windows":
        return []
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        return []

    lines = []
    for line in result.stdout.splitlines():
        if "gta" in line.lower():
            lines.append(line.strip())
    return lines


def find_all_saves(verbose=True):
    if verbose:
        _log("=" * 50)
        _log("ПОИСК СОХРАНЕНИЙ GTA 2")
        _log("=" * 50)

    all_found = []
    all_found.extend(scan_known_dirs(verbose))
    all_found.extend(scan_registry(verbose))

    if not all_found:
        if verbose:
            _log("Ничего не найдено в известных местах, запускаю глубокий поиск...")
        drives = []
        if platform.system() == "Windows":
            for letter in "CDEFGH":
                root = f"{letter}:\\"
                if os.path.isdir(root):
                    drives.append(root)
        else:
            drives = ["/"]

        for drive in drives:
            all_found.extend(scan_drive(drive, MAX_SCAN_DEPTH, verbose))

    # дедупликация
    seen = set()
    unique = []
    for f in all_found:
        key = os.path.normpath(f).lower()
        if key not in seen and os.path.isfile(f):
            seen.add(key)
            unique.append(f)

    if verbose:
        _log(f"Итого найдено: {len(unique)}")

    return unique


def latest_save(verbose=False):
    saves = find_all_saves(verbose=verbose)
    if not saves:
        return None
    return max(saves, key=os.path.getmtime)


# ============================================================
# АНАЛИЗ ФАЙЛА
# ============================================================

def analyze_file(path, verbose=False):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return {"path": path, "error": str(e)}

    info = {
        "path": path,
        "name": os.path.basename(path),
        "size": len(data),
        "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
        "hash": _file_hash(path),
        "header_hex": data[:32].hex(),
        "strings": [],
        "int_candidates": [],
        "signatures": [],
    }

    strings = _extract_ascii_strings(data, min_len=4, max_count=50, limit_bytes=8192)
    info["strings"] = [{"offset": o, "text": s} for o, s in strings]

    candidates = _extract_int32_candidates(data, start=0, end=min(len(data), 8192))
    info["int_candidates"] = [{"offset": o, "value": v} for o, v in candidates[:200]]

    signatures = {
        b"GTA2": "GTA2",
        b"gta2": "gta2",
        b"SAVE": "SAVE",
        b"Rockstar": "Rockstar",
        b"PLAYER": "PLAYER",
        b"SCORE": "SCORE",
    }
    for sig, label in signatures.items():
        idx = data.find(sig)
        if idx != -1:
            info["signatures"].append({"name": label, "offset": idx})

    return info


def _find_string_offset(info, targets):
    for entry in info.get("strings", []):
        text = entry["text"].lower()
        for t in targets:
            if t in text:
                return entry["offset"], entry["text"]
    return None, None


def _find_value_offsets(info, value):
    return [
        c["offset"] for c in info.get("int_candidates", [])
        if c["value"] == value
    ]


# ============================================================
# ПАРСИНГ
# ============================================================

SAVE_FIELD_MAP = {
    "name_offset": None,
    "money": None,
    "district": None,
    "day": None,
    "kills": None,
    "police_kills": None,
    "cars_destroyed": None,
    "missions_done": None,
}


def _load_field_map():
    cache = _load_cache()
    return cache.get("field_map", SAVE_FIELD_MAP)


def _save_field_map(field_map):
    cache = _load_cache()
    cache["field_map"] = field_map
    _save_cache(cache)


def _read_int(data, offset):
    if offset is None:
        return 0
    if offset + 4 > len(data):
        return 0
    try:
        return struct.unpack("<i", data[offset:offset + 4])[0]
    except struct.error:
        return 0


def parse_save(path, verbose=False):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return {"path": path, "error": str(e)}

    field_map = _load_field_map()

    stats = {
        "file": os.path.basename(path),
        "path": path,
        "size": len(data),
        "hash": _file_hash(path),
        "parsed_at": datetime.now().isoformat(),
    }

    # имя игрока
    name = ""
    if field_map.get("name_offset") is not None:
        name = _read_cstring(data, field_map["name_offset"], 32)
    if not name:
        strings = _extract_ascii_strings(data, min_len=3, max_count=20, limit_bytes=512)
        for offset, text in strings:
            if text.isprintable() and 3 <= len(text) <= 20:
                name = text
                break
    stats["name"] = name

    # числовые поля
    stats["money"] = _read_int(data, field_map.get("money"))
    stats["district"] = _read_int(data, field_map.get("district"))
    stats["day"] = _read_int(data, field_map.get("day"))
    stats["kills"] = _read_int(data, field_map.get("kills"))
    stats["police_kills"] = _read_int(data, field_map.get("police_kills"))
    stats["cars_destroyed"] = _read_int(data, field_map.get("cars_destroyed"))
    stats["missions_done"] = _read_int(data, field_map.get("missions_done"))

    if verbose:
        _log(f"Парсинг {stats['file']}:")
        for k in ("name", "money", "district", "day", "kills",
                  "police_kills", "cars_destroyed", "missions_done"):
            _log(f"  {k:18} = {stats[k]}")

    return stats


def get_stats_if_changed(last_hash, verbose=False):
    path = latest_save(verbose=verbose)
    if not path:
        return None, last_hash

    current_hash = _file_hash(path)
    if current_hash is None:
        return None, last_hash

    if current_hash == last_hash:
        return None, last_hash

    stats = parse_save(path, verbose=verbose)
    return stats, current_hash


# ============================================================
# КАЛИБРОВКА
# ============================================================

def calibrate(path=None, verbose=True):
    if path is None:
        path = latest_save(verbose=verbose)
    if not path:
        print("Сохранения не найдены")
        return None

    print()
    print("=" * 50)
    print(f"КАЛИБРОВКА: {path}")
    print("=" * 50)

    info = analyze_file(path, verbose=True)

    print()
    print("Строки в первых 8 КБ:")
    for entry in info["strings"][:30]:
        print(f"  0x{entry['offset']:04x}  {entry['text']}")

    print()
    print("Числовые кандидаты (первые 50):")
    for entry in info["int_candidates"][:50]:
        print(f"  0x{entry['offset']:04x}  {entry['value']}")

    print()
    print("Введи реальные значения из игры (Enter — пропустить):")

    field_map = {}

    for field, prompt in [
        ("name_offset", "Смещение имени игрока (hex или dec, напр. 4)"),
        ("money", "Смещение денег"),
        ("district", "Смещение района"),
        ("day", "Смещение дня недели"),
        ("kills", "Смещение убийств"),
        ("police_kills", "Смещение убийств полиции"),
        ("cars_destroyed", "Смещение разрушенных машин"),
        ("missions_done", "Смещение выполненных миссий"),
    ]:
        val = input(f"  {prompt}: ").strip()
        if not val:
            continue
        try:
            if val.lower().startswith("0x"):
                field_map[field] = int(val, 16)
            else:
                field_map[field] = int(val)
        except ValueError:
            print(f"    пропущено (некорректное значение: {val})")

    if field_map:
        current = _load_field_map()
        current.update(field_map)
        _save_field_map(current)
        print()
        print("Калибровка сохранена в", CACHE_FILE)
        print("Значения:", json.dumps(current, ensure_ascii=False, indent=2))
        return current

    print("Ничего не введено, калибровка не сохранена")
    return None


def auto_calibrate(path=None, expected=None):
    if path is None:
        path = latest_save(verbose=False)
    if not path or not expected:
        return None

    info = analyze_file(path)
    field_map = _load_field_map()

    for field, value in expected.items():
        if field == "name":
            continue
        offsets = _find_value_offsets(info, value)
        if offsets:
            field_map[field] = offsets[0]

    _save_field_map(field_map)
    return field_map


# ============================================================
# ДИАГНОСТИКА
# ============================================================

def diagnostic(verbose=True):
    report = {
        "started_at": datetime.now().isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "cwd": os.getcwd(),
        "candidate_dirs_existing": [],
        "candidate_dirs_missing": [],
        "saves_found": [],
        "saves_analyzed": [],
        "processes": [],
        "cache_field_map": _load_field_map(),
    }

    for d in _candidate_dirs():
        if os.path.isdir(d):
            report["candidate_dirs_existing"].append(d)
        else:
            report["candidate_dirs_missing"].append(d)

    saves = find_all_saves(verbose=verbose)
    report["saves_found"] = saves

    for s in saves:
        info = analyze_file(s)
        report["saves_analyzed"].append({
            "path": s,
            "size": info.get("size"),
            "hash": info.get("hash"),
            "strings_count": len(info.get("strings", [])),
            "candidates_count": len(info.get("int_candidates", [])),
            "signatures": info.get("signatures", []),
        })

    report["processes"] = scan_gta2_process()

    try:
        with open(DIAGNOSTIC_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        if verbose:
            _log(f"Отчёт записан: {os.path.abspath(DIAGNOSTIC_FILE)}")
    except OSError:
        pass

    return report


# ============================================================
# CLI
# ============================================================

def _print_help():
    print("Использование:")
    print("  python gta2_reader.py find           — найти все сохранения")
    print("  python gta2_reader.py latest         — показать самый свежий сейв")
    print("  python gta2_reader.py parse          — распарсить свежий сейв")
    print("  python gta2_reader.py analyze <file> — детальный анализ файла")
    print("  python gta2_reader.py calibrate      — калибровка смещений")
    print("  python gta2_reader.py diagnostic     — полная диагностика")
    print("  python gta2_reader.py check          — проверить свежий сейв на изменения")
    print("  python gta2_reader.py process        — список процессов GTA 2")


def _cli():
    if len(sys.argv) < 2:
        _print_help()
        return

    cmd = sys.argv[1].lower()

    if cmd == "find":
        saves = find_all_saves(verbose=True)
        print()
        print(f"Найдено: {len(saves)}")
        for s in saves:
            size = os.path.getsize(s)
            mtime = datetime.fromtimestamp(os.path.getmtime(s)).strftime("%d.%m.%Y %H:%M")
            print(f"  {mtime}  {size:>10}  {s}")

    elif cmd == "latest":
        s = latest_save(verbose=True)
        if s:
            print()
            print("Свежий сейв:", s)
        else:
            print("Не найдено")

    elif cmd == "parse":
        s = latest_save(verbose=True)
        if not s:
            print("Не найдено")
            return
        stats = parse_save(s, verbose=True)
        print()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif cmd == "analyze":
        if len(sys.argv) < 3:
            print("Укажи путь к файлу")
            return
        info = analyze_file(sys.argv[2], verbose=True)
        print(json.dumps(info, ensure_ascii=False, indent=2)[:5000])

    elif cmd == "calibrate":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        calibrate(path=path, verbose=True)

    elif cmd == "diagnostic":
        diagnostic(verbose=True)

    elif cmd == "check":
        cache = _load_cache()
        last_hash = cache.get("last_hash")
        stats, new_hash = get_stats_if_changed(last_hash, verbose=True)
        if stats:
            cache["last_hash"] = new_hash
            _save_cache(cache)
            print()
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print("Изменений нет")

    elif cmd == "process":
        procs = scan_gta2_process()
        if procs:
            for p in procs:
                print(p)
        else:
            print("GTA 2 не запущена")

    else:
        _print_help()


if __name__ == "__main__":
    _cli()
