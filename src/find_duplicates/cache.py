import sys
import sqlite3
from pathlib import Path


class FileCache:
    """基于 SQLite 的文件哈希缓存，用于避免重复读取未修改的文件内容。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(db_path)
            self._init_db()
        except sqlite3.Error as e:
            print(
                f"[警告] 无法初始化缓存数据库: {e}，将无法使用缓存功能。",
                file=sys.stderr,
            )

    def _init_db(self):
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(file_cache)")
            rows = cursor.fetchall()
            columns = {row[1] for row in rows}
            pk_columns = {row[1] for row in rows if row[5] > 0}
            
            expected_columns = {"filepath", "size", "mtime", "hash", "algorithm"}
            expected_pks = {"filepath", "algorithm"}
            
            if columns != expected_columns or pk_columns != expected_pks:
                with self.conn:
                    self.conn.execute("DROP TABLE IF EXISTS file_cache")
                    self.conn.execute("""
                        CREATE TABLE file_cache (
                            filepath TEXT,
                            size INTEGER,
                            mtime REAL,
                            hash TEXT,
                            algorithm TEXT,
                            PRIMARY KEY (filepath, algorithm)
                        )
                    """)
        except sqlite3.Error as e:
            print(
                f"[警告] 无法初始化缓存数据库: {e}，将无法使用缓存功能。",
                file=sys.stderr,
            )

    def get_hash(self, filepath: Path, algorithm: str) -> str | None:
        """从缓存中检索哈希值，如果文件未修改且算法匹配则返回哈希，否则返回 None。"""
        if not self.conn:
            return None
        try:
            stat = filepath.stat()
            current_size = stat.st_size
            current_mtime = stat.st_mtime
            normalized_path = filepath.resolve().as_posix()

            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT size, mtime, hash FROM file_cache WHERE filepath = ? AND algorithm = ?",
                (normalized_path, algorithm),
            )
            row = cursor.fetchone()
            if row:
                cached_size, cached_mtime, cached_hash = row
                # 浮点数比对，保留微小容差
                if (
                    current_size == cached_size
                    and abs(current_mtime - cached_mtime) < 1e-4
                ):
                    return cached_hash
        except (OSError, sqlite3.Error):
            pass
        return None

    def update_hash(self, filepath: Path, file_hash: str, algorithm: str):
        """将文件的当前状态、哈希值和算法更新到数据库缓存中。"""
        if not self.conn:
            return
        try:
            stat = filepath.stat()
            normalized_path = filepath.resolve().as_posix()
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO file_cache (filepath, size, mtime, hash, algorithm) VALUES (?, ?, ?, ?, ?)",
                    (normalized_path, stat.st_size, stat.st_mtime, file_hash, algorithm),
                )
        except (OSError, sqlite3.Error):
            pass

    def prune_stale_records(self, include_dirs, keep_paths):
        """
        清理缓存中在当前扫描目录下但实际已被删除或改名的文件记录。
        """
        if not self.conn:
            return
        try:
            # 1. 查找当前扫描目录下所有的缓存记录
            cached_paths_in_scope = set()
            cursor = self.conn.cursor()

            for root_dir in include_dirs:
                root_path_str = Path(root_dir).resolve().as_posix()
                # 匹配目录本身或其子文件/子目录
                cursor.execute(
                    "SELECT filepath FROM file_cache WHERE filepath = ? OR filepath LIKE ?",
                    (root_path_str, root_path_str + "/%"),
                )
                for row in cursor.fetchall():
                    cached_paths_in_scope.add(row[0])

            # 2. 找出已不存在（未被 keep_paths 记录）的缓存路径
            keep_paths_normalized = {Path(p).resolve().as_posix() for p in keep_paths}
            stale_paths = cached_paths_in_scope - keep_paths_normalized

            if stale_paths:
                # 3. 分批删除
                stale_list = list(stale_paths)
                batch_size = 999
                with self.conn:
                    for i in range(0, len(stale_list), batch_size):
                        batch = stale_list[i : i + batch_size]
                        placeholders = ",".join("?" for _ in batch)
                        self.conn.execute(
                            f"DELETE FROM file_cache WHERE filepath IN ({placeholders})",
                            batch,
                        )
        except sqlite3.Error:
            pass

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass
