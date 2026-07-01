import pytest
from find_duplicates.cache import FileCache


@pytest.fixture
def cache_db(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = FileCache(str(db_file))
    yield cache
    cache.close()


def test_cache_init(cache_db):
    assert cache_db.conn is not None
    # 确保表被创建
    cursor = cache_db.conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='file_cache'"
    )
    assert cursor.fetchone() is not None


def test_cache_get_and_update(cache_db, tmp_path):
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("hello world")

    # 初始状态：未缓存
    assert cache_db.get_hash(file_path) is None

    # 缓存哈希
    test_hash = "5ad9cbcd"
    cache_db.update_hash(file_path, test_hash)

    # 命中缓存
    assert cache_db.get_hash(file_path) == test_hash

    # 改变文件大小 -> 缓存失效
    file_path.write_text("hello world extra")
    assert cache_db.get_hash(file_path) is None

    # 更新新状态下的缓存
    new_hash = "a49d4dd3"
    cache_db.update_hash(file_path, new_hash)
    assert cache_db.get_hash(file_path) == new_hash

    # 改变修改时间 -> 缓存失效
    # 我们通过修改文件时间属性模拟
    stat = file_path.stat()
    current_mtime = stat.st_mtime
    # 人为设置一个过去的修改时间
    past_mtime = current_mtime - 100.0
    import os

    os.utime(file_path, (past_mtime, past_mtime))
    assert cache_db.get_hash(file_path) is None


def test_cache_prune_stale_records(cache_db, tmp_path):
    # 创建三个文件并缓存
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f3 = tmp_path / "other_dir" / "file3.txt"

    f1.parent.mkdir(parents=True, exist_ok=True)
    f3.parent.mkdir(parents=True, exist_ok=True)

    f1.write_text("1")
    f2.write_text("2")
    f3.write_text("3")

    cache_db.update_hash(f1, "hash1")
    cache_db.update_hash(f2, "hash2")
    cache_db.update_hash(f3, "hash3")

    # 检验全部缓存成功
    assert cache_db.get_hash(f1) == "hash1"
    assert cache_db.get_hash(f2) == "hash2"
    assert cache_db.get_hash(f3) == "hash3"

    # 清理非活跃记录
    # 如果扫描 include_dirs = [tmp_path]
    # 保留的文件列表只有 f1 和 f3
    # 那么 f2 应该从缓存数据库中清理掉
    cache_db.prune_stale_records([str(tmp_path)], [f1, f3])

    # f1, f3 仍在缓存中
    assert cache_db.get_hash(f1) == "hash1"
    assert cache_db.get_hash(f3) == "hash3"

    # f2 被清理了，就算文件本身没变，再次调用 get_hash 也应当因为缓存表中无记录而返回 None
    assert cache_db.get_hash(f2) is None
