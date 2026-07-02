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

def test_validate_selections_valid(tmp_path):
    f1 = tmp_path / "f1.txt"
    f1.write_text("content1")
    f2 = tmp_path / "f2.txt"
    f2.write_text("content2")
    
    duplicates = {"h1": [str(f1), str(f2)]}
    keep = {str(f1)}
    trash = {str(f2)}
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

def test_validate_selections_overlap():
    duplicates = {"h1": ["f1.txt", "f2.txt"]}
    keep = {"f1.txt"}
    trash = {"f1.txt"}
    err = validate_selections(duplicates, keep, trash)
    assert err is not None
    assert "文件同时被标记为保留和删除" in err

def test_validate_selections_kept_files_not_on_disk(tmp_path):
    # If the file not marked for deletion does not exist, we should get safety error
    f1 = tmp_path / "f1_nonexistent.txt" # Not on disk
    f2 = tmp_path / "f2.txt"
    f2.write_text("content2")
    
    duplicates = {"h1": [str(f1), str(f2)]}
    keep = {str(f1)}
    trash = {str(f2)}
    
    err = validate_selections(duplicates, keep, trash)
    assert err is not None
    assert "保留的文件均在磁盘上不存在" in err

@patch("find_duplicates.handler.core.send2trash.send2trash")
def test_recycle_files_mocked(mock_send2trash, tmp_path):
    f1 = tmp_path / "t1.txt"
    f1.write_text("content")
    
    mock_send2trash.return_value = None
    count, size = recycle_files([str(f1)])
    assert count == 1
    assert size == 7
    mock_send2trash.assert_called_once_with(str(f1))

@patch("find_duplicates.handler.core.send2trash.send2trash")
def test_recycle_files_exception_handling(mock_send2trash, tmp_path, capsys):
    f1 = tmp_path / "t1.txt"
    f1.write_text("content1")
    f2 = tmp_path / "t2.txt"
    f2.write_text("content2")
    
    # Let send2trash raise an Exception on f1 but succeed on f2
    def side_effect(path):
        if path == str(f1):
            raise Exception("Access Denied")
        return None
        
    mock_send2trash.side_effect = side_effect
    
    count, size = recycle_files([str(f1), str(f2)])
    # f1 failed but f2 succeeded
    assert count == 1
    assert size == 8  # t2 size
    
    # Check that warning was printed to stderr
    captured = capsys.readouterr()
    assert "警告：物理移动文件至回收站失败" in captured.err
    assert "Access Denied" in captured.err

def test_recycle_files_ignores_non_existent_paths():
    # If path does not exist, recycle_files should skip it without throwing exceptions
    count, size = recycle_files(["/nonexistent/path/here.txt"])
    assert count == 0
    assert size == 0

