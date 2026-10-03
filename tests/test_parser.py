"""Uji parser pada format access log nyata (Combined Log Format)."""
from src.log_parser import merge_results, parse_chunk

SAMPLE = [
    '54.36.149.41 - - [22/Jan/2019:03:56:14 +0330] "GET /a HTTP/1.1" 200 10 "-" "UA" "-"',
    '31.56.96.51 - - [22/Jan/2019:03:56:16 +0330] "GET /b HTTP/1.1" 404 20 "-" "UA" "-"',
    '10.0.0.1 - - [22/Jan/2019:03:56:18 +0330] "POST /timeout-x HTTP/1.1" 503 30 "-" "UA" "-"',
]


def test_parse_chunk():
    r = parse_chunk(SAMPLE, keyword="timeout")
    assert r["total_baris"] == 3, r
    assert r["status"] == {"200": 1, "404": 1, "503": 1}, r["status"]
    assert r["ip"]["54.36.149.41"] == 1
    assert r["keyword"] == 1, r  # hanya baris timeout (case-insensitive)
    assert all(v == 0 for v in r["levels"].values()), r["levels"]


def test_merge():
    a = parse_chunk(SAMPLE[:2])
    b = parse_chunk(SAMPLE[2:])
    m = merge_results([a, b])
    assert m["total_baris"] == 3
    assert m["status"]["200"] == 1 and m["keyword"] == 1


if __name__ == "__main__":
    test_parse_chunk()
    test_merge()
    print("test_parser OK")
