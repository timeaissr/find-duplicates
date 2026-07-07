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
    assert cache_db.get_hash(file_path, "xxh3") is None

    # 缓存哈希
    test_hash = "5ad9cbcd"
    cache_db.update_hash(file_path, test_hash, "xxh3")

    # 命中缓存
    assert cache_db.get_hash(file_path, "xxh3") == test_hash

    # 改变文件大小 -> 缓存失效
    file_path.write_text("hello world extra")
    assert cache_db.get_hash(file_path, "xxh3") is None

    # 更新新状态下的缓存
    new_hash = "a49d4dd3"
    cache_db.update_hash(file_path, new_hash, "xxh3")
    assert cache_db.get_hash(file_path, "xxh3") == new_hash

    # 改变修改时间 -> 缓存失效
    # 我们通过修改文件时间属性模拟
    stat = file_path.stat()
    current_mtime = stat.st_mtime
    # 人为设置一个过去的修改时间
    past_mtime = current_mtime - 100.0
    import os

    os.utime(file_path, (past_mtime, past_mtime))
    assert cache_db.get_hash(file_path, "xxh3") is None


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

    cache_db.update_hash(f1, "hash1", "xxh3")
    cache_db.update_hash(f2, "hash2", "xxh3")
    cache_db.update_hash(f3, "hash3", "xxh3")

    # 检验全部缓存成功
    assert cache_db.get_hash(f1, "xxh3") == "hash1"
    assert cache_db.get_hash(f2, "xxh3") == "hash2"
    assert cache_db.get_hash(f3, "xxh3") == "hash3"

    # 清理非活跃记录
    # 如果扫描 include_dirs = [tmp_path]
    # 保留的文件列表只有 f1 和 f3
    # 那么 f2 应该从缓存数据库中清理掉
    cache_db.prune_stale_records([str(tmp_path)], [f1, f3])

    # f1, f3 仍在缓存中
    assert cache_db.get_hash(f1, "xxh3") == "hash1"
    assert cache_db.get_hash(f3, "xxh3") == "hash3"

    # f2 被清理了，就算文件本身没变，再次调用 get_hash 也应当因为缓存表中无记录而返回 None
    assert cache_db.get_hash(f2, "xxh3") is None


def test_cache_schema_validation_and_recreate(tmp_path):
    import sqlite3
    db_file = tmp_path / "test_recreate.db"
    
    # 模拟旧版本没有 algorithm 字段的表结构
    conn = sqlite3.connect(str(db_file))
    with conn:
        conn.execute("CREATE TABLE file_cache (filepath TEXT PRIMARY KEY, size INTEGER, mtime REAL, hash TEXT)")
        conn.execute("INSERT INTO file_cache VALUES ('test_path', 10, 1.0, 'old_hash')")
    conn.close()

    # 实例化 FileCache，应当触发 DROP 表并重新创建表结构
    cache = FileCache(str(db_file))
    cursor = cache.conn.cursor()
    cursor.execute("PRAGMA table_info(file_cache)")
    rows = cursor.fetchall()
    columns = {row[1] for row in rows}
    pk_columns = {row[1] for row in rows if row[5] > 0}
    assert columns == {"filepath", "size", "mtime", "hash", "algorithm"}
    assert pk_columns == {"filepath", "algorithm"}
    
    # 确认旧数据已经被清空
    cursor.execute("SELECT COUNT(*) FROM file_cache")
    assert cursor.fetchone()[0] == 0
    cache.close()


def test_cache_algorithm_isolation(cache_db, tmp_path):
    file_path = tmp_path / "iso_file.txt"
    file_path.write_text("isolate")

    # 写入 xxh3 缓存
    cache_db.update_hash(file_path, "xxh3_hash_val", "xxh3")
    
    # 当读取 blake3 时，应当隔离并返回 None
    assert cache_db.get_hash(file_path, "blake3") is None

    # 读取 xxh3 时，可以正常命中
    assert cache_db.get_hash(file_path, "xxh3") == "xxh3_hash_val"

    # 写入 blake3 缓存
    cache_db.update_hash(file_path, "blake3_hash_val", "blake3")

    # 读取 blake3 时，命中新值
    assert cache_db.get_hash(file_path, "blake3") == "blake3_hash_val"
    # 读取 xxh3 时，由于是联合主键，旧的 xxh3 缓存仍然存在且能命中
    assert cache_db.get_hash(file_path, "xxh3") == "xxh3_hash_val"


def test_cache_init_failure():
    import pytest
    # 使用包含不存在父目录的路径，强制 sqlite3 抛出 OperationalError
    with pytest.raises(RuntimeError) as exc_info:
        FileCache("nonexistent_dir_12345/cache.db")
    assert "无法初始化缓存数据库" in str(exc_info.value)


