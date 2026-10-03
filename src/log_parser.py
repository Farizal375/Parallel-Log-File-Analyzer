"""Fungsi parsing log bersama (dipakai semua mode).

Format nyata (GATE 1): Combined Log Format, contoh:
  54.36.149.41 - - [22/Jan/2019:03:56:14 +0330] "GET /x HTTP/1.1" 200 1234 "-" "UA" "-"
  -> IP = token pertama, status = 3 digit setelah request dalam kutip.

Keputusan #3: level INFO/WARN/ERROR/DEBUG tidak ada di access log,
selalu 0. Key tetap di-output untuk konsistensi, bukan metrik utama.
Metrik utama: status_code, top_ip, keyword (default "timeout", case-insensitive).
"""
import re

LEVELS = ("INFO", "WARN", "ERROR", "DEBUG")
_LEVEL_RES = {lv: re.compile(r"\b" + lv + r"\b") for lv in LEVELS}
_IP_RE = re.compile(r"^\s*(\S+)")
_STATUS_RE = re.compile(r'"\s(\d{3})\s')


def parse_chunk(lines: list[str], keyword: str = "timeout") -> dict:
    levels = {lv: 0 for lv in LEVELS}
    status: dict[str, int] = {}
    ip: dict[str, int] = {}
    kw = keyword.lower()
    kw_count = 0
    total = 0
    for line in lines:
        total += 1
        for lv, rx in _LEVEL_RES.items():
            if rx.search(line):
                levels[lv] += 1
        m = _IP_RE.match(line)
        if m:
            addr = m.group(1)
            ip[addr] = ip.get(addr, 0) + 1
        s = _STATUS_RE.search(line)
        if s:
            code = s.group(1)
            status[code] = status.get(code, 0) + 1
        if kw and kw in line.lower():
            kw_count += 1
    return {
        "total_baris": total,
        "levels": levels,
        "status": status,
        "ip": ip,
        "keyword": kw_count,
    }


def merge_results(parts: list[dict]) -> dict:
    total = 0
    levels = {lv: 0 for lv in LEVELS}
    status: dict[str, int] = {}
    ip: dict[str, int] = {}
    kw = 0
    for p in parts:
        total += int(p.get("total_baris", 0))
        for lv in LEVELS:
            levels[lv] += int(p.get("levels", {}).get(lv, 0))
        for k, v in p.get("status", {}).items():
            status[k] = status.get(k, 0) + int(v)
        for k, v in p.get("ip", {}).items():
            ip[k] = ip.get(k, 0) + int(v)
        kw += int(p.get("keyword", 0))
    return {"total_baris": total, "levels": levels, "status": status, "ip": ip, "keyword": kw}


if __name__ == "__main__":
    demo = ['127.0.0.1 - - [22/Jan/2019:00:00:00 +0000] "GET /a HTTP/1.1" 200 10 "-" "UA" "-"']
    print(merge_results([parse_chunk(demo)]))
