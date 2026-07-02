import json
from unittest.mock import patch
from find_duplicates.handler.core import load_json_report, validate_selections, recycle_files

def test_load_json_report(tmp_path):
    report_file = tmp_path / "report.json"
    dummy_data = {
        "summary": {"total_files": 10},
        "duplicates": {
            "hash123": ["file1.txt", "file2.txt"]
        }
    }
    report_file.write_text(json.dumps(dummy_data))
    
    summary, duplicates = load_json_report(report_file)
    assert summary["total_files"] == 10
    assert "hash123" in duplicates
    assert len(duplicates["hash123"]) == 2

def test_validate_selections_empty():
    duplicates = {"h1": ["f1.txt", "f2.txt"]}
    keep = {"f1.txt"}
    trash = {"f2.txt"}
    # Should pass (returns None)
    assert validate_selections(duplicates, keep, trash) is None

def test_validate_selections_must_keep_one():
    duplicates = {"h1": ["f1.txt", "f2.txt"]}
    keep = set()
    trash = {"f1.txt", "f2.txt"}
    # Should return an error message
    err = validate_selections(duplicates, keep, trash)
    assert err is not None
    assert "必须至少保留一个文件" in err

@patch("find_duplicates.handler.core.send2trash.send2trash")
def test_recycle_files_mocked(mock_send2trash, tmp_path):
    f1 = tmp_path / "t1.txt"
    f1.write_text("content")
    
    mock_send2trash.return_value = None
    count, size = recycle_files([str(f1)])
    assert count == 1
    assert size == 7
    mock_send2trash.assert_called_once_with(str(f1))
