from find_duplicates.scanner import scan_duplicates_generator


def test_scanner_finds_duplicates(tmp_path):
    # 创建一些测试文件
    dir1 = tmp_path / "dir1"
    dir1.mkdir()

    file_a = dir1 / "file_a.txt"
    file_a.write_text("common content")

    file_b = dir1 / "file_b.txt"
    file_b.write_text("common content")  # 重复内容

    file_unique = dir1 / "unique.txt"
    file_unique.write_text("unique content")

    # 运行扫描生成器
    gen = scan_duplicates_generator([str(dir1)], [])

    events = []
    duplicates = {}

    while True:
        try:
            event = next(gen)
            events.append(event)
        except StopIteration as e:
            duplicates, cache_hits, total_files, file_list = e.value
            break

    # 验证事件序列
    assert len(events) > 0
    assert events[0] == ("count_start", None)
    assert events[1] == ("count_end", 3)

    # 验证扫描结果
    assert len(duplicates) == 1
    # 应该有一组重复文件
    hashes = list(duplicates.keys())
    assert len(duplicates[hashes[0]]) == 2
    assert str(file_a.resolve()) in duplicates[hashes[0]]
    assert str(file_b.resolve()) in duplicates[hashes[0]]
    assert str(file_unique.resolve()) not in duplicates[hashes[0]]

    assert total_files == 3


def test_scanner_with_exclusions(tmp_path):
    dir_root = tmp_path / "root"
    dir_root.mkdir()

    dir_ex = dir_root / "exclude_this"
    dir_ex.mkdir()

    file_a = dir_root / "file_a.txt"
    file_a.write_text("dup")

    file_b = dir_ex / "file_b.txt"
    file_b.write_text("dup")

    # 排除整个 exclude_this 目录
    gen = scan_duplicates_generator([str(dir_root)], [str(dir_ex)])
    while True:
        try:
            next(gen)
        except StopIteration as e:
            duplicates, _, total_files, _ = e.value
            break

    # 应该找不到重复，因为 file_b 被排除了，总共只扫描到 1 个文件
    assert len(duplicates) == 0
    assert total_files == 1


def test_scanner_with_blake3(tmp_path):
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    f1 = dir1 / "f1.txt"
    f1.write_text("same content")
    f2 = dir1 / "f2.txt"
    f2.write_text("same content")

    gen = scan_duplicates_generator([str(dir1)], [], algorithm="blake3")
    while True:
        try:
            next(gen)
        except StopIteration as e:
            duplicates, _, _, _ = e.value
            break

    # 验证产生了一组重复且哈希长度为 64 (BLAKE3 hex)
    assert len(duplicates) == 1
    hsh = list(duplicates.keys())[0]
    assert len(hsh) == 64
