import json
import csv
from find_duplicates.output import write_results_to_file


def test_write_json_output(tmp_path):
    out_file = tmp_path / "output.json"
    duplicates = {"hash_xxx": ["/path/a", "/path/b"]}

    write_results_to_file(
        output_path=str(out_file),
        duplicates=duplicates,
        elapsed_time=1.23,
        total_files=5,
        include_dirs=["/scan/dir"],
        algorithm="blake3"
    )

    assert out_file.exists()

    with out_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["summary"]["total_files"] == 5
    assert data["summary"]["duplicate_groups"] == 1
    assert data["summary"]["algorithm"] == "blake3"
    assert data["duplicates"] == duplicates


def test_write_csv_output(tmp_path):
    out_file = tmp_path / "output.csv"
    duplicates = {"hash_xxx": ["/path/a", "/path/b"]}

    write_results_to_file(
        output_path=str(out_file),
        duplicates=duplicates,
        elapsed_time=1.23,
        total_files=5,
        include_dirs=["/scan/dir"],
    )

    assert out_file.exists()

    with out_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0] == ["Group", "Hash", "FilePath"]
    assert rows[1] == ["1", "hash_xxx", "/path/a"]
    assert rows[2] == ["1", "hash_xxx", "/path/b"]


def test_write_txt_output(tmp_path):
    out_file = tmp_path / "output.txt"
    duplicates = {"hash_xxx": ["/path/a", "/path/b"]}

    write_results_to_file(
        output_path=str(out_file),
        duplicates=duplicates,
        elapsed_time=1.23,
        total_files=5,
        include_dirs=["/scan/dir"],
        algorithm="blake3"
    )

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    assert "扫描完成：共发现 1 组重复文件" in content
    assert "BLAKE3: hash_xxx" in content
    assert "  - /path/a" in content
    assert "执行总耗时: 1.23 秒" in content

