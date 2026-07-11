import sys
import time
import argparse
from pathlib import Path

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.tree import Tree
from rich.panel import Panel

from .cache import FileCache
from .scanner import scan_duplicates_generator
from .output import write_results_to_file


def format_size(size_in_bytes: int) -> str:
    """格式化文件大小为易读的单位。"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024.0:
            if unit == "B":
                return f"{int(size_in_bytes)} {unit}"
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"


def main():
    parser = argparse.ArgumentParser(
        description="使用 XXH3-128 或 BLAKE3 算法在多个文件夹中查找内容重复的文件。"
    )

    parser.add_argument(
        "-i",
        "--include",
        action="append",
        required=True,
        help="要包含（扫描）的文件夹或文件路径（若有多个，请多次使用 -i 或 --include）",
    )

    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=None,
        help="要排除的文件夹路径（若有多个，请多次使用 -e 或 --exclude）",
    )

    parser.add_argument(
        "-o",
        "--output",
        action="append",
        default=None,
        help="指定输出文件路径，可多次指定以输出多种格式。后缀必须是 .txt, .json, .csv 之一（强制校验，不区分大小写）",
    )

    parser.add_argument(
        "--cache-file",
        default=None,
        help="指定 SQLite 缓存文件路径。若不指定，则不启用缓存（退化为完全物理扫描）。若指定但初始化失败，则报错并终止程序",
    )

    parser.add_argument(
        "--algorithm",
        choices=["xxh3", "blake3"],
        default="xxh3",
        help="指定查重使用的哈希算法：xxh3 (默认, XXH3-128) 或 blake3 (BLAKE3)",
    )

    args = parser.parse_args()

    includes = args.include if args.include else []
    excludes = args.exclude if args.exclude else []
    outputs = args.output if args.output else []
    cache_file = args.cache_file

    # 强制校验输出路径的后缀
    for out in outputs:
        p = Path(out)
        suffix = p.suffix.lower()
        if suffix not in (".txt", ".json", ".csv"):
            parser.error(
                f"不支持的输出文件格式: '{out}'。后缀必须是 .txt, .json, .csv 之一。"
            )

    console = Console()

    start_time = time.perf_counter()
    duplicates = {}
    cache_hits = 0
    total_files = 0
    file_list = []

    try:
        # 初始化缓存
        cache = None
        if cache_file:
            cache = FileCache(cache_file)

        # 使用 rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            TimeRemainingColumn(),
            TextColumn("[dim]{task.fields[current_file]}"),
            console=console,
            transient=True,  # 扫描完成后自动清除进度条，不污染输出
        ) as progress:
            task_id = None

            # 调用扫描生成器
            scanner_gen = scan_duplicates_generator(
                includes, excludes, cache=cache, cache_file_path=cache_file, algorithm=args.algorithm
            )

            while True:
                try:
                    event = next(scanner_gen)
                    event_type = event[0]

                    if event_type == "count_start":
                        task_id = progress.add_task(
                            description="正在统计文件数...", total=None, current_file=""
                        )
                    elif event_type == "count_end":
                        total_count = event[1]
                        progress.update(
                            task_id, description="准备计算哈希...", total=total_count
                        )
                    elif event_type == "hash_progress":
                        _, processed, total, path_str, _ = event
                        # 截断路径以防止把终端挤乱
                        terminal_width = console.width
                        # 预留给进度条各列的空间大约为 65 字符
                        max_path_len = max(10, terminal_width - 65)
                        display_path = path_str
                        if len(path_str) > max_path_len:
                            display_path = "..." + path_str[-(max_path_len - 3) :]

                        progress.update(
                            task_id,
                            description="正在读取文件...",
                            completed=processed,
                            total=total,
                            current_file=display_path,
                        )
                except StopIteration as e:
                    # 获取生成器的 return 返回值
                    duplicates, cache_hits, total_files, file_list = e.value
                    break

    except RuntimeError as e:
        Console(stderr=True).print(f"[bold red][错误] {e}[/bold red]")
        if cache:
            cache.close()
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]操作被用户终止。[/bold yellow]")
        if cache:
            cache.close()
        sys.exit(1)

    elapsed_time = time.perf_counter() - start_time

    # 清理失效缓存并关闭
    if cache:
        cache.prune_stale_records(includes, file_list)
        cache.close()

    # 渲染输出到终端
    if not duplicates:
        if console.is_terminal:
            console.print(
                Panel(
                    "[bold green]扫描完成：未发现内容重复的文件。[/bold green]",
                    subtitle=f"耗时: {elapsed_time:.2f} 秒",
                    expand=False,
                )
            )
        else:
            print("扫描完成：未发现内容重复的文件。")
            print(f"执行总耗时: {elapsed_time:.2f} 秒")
    else:
        if console.is_terminal:
            tree = Tree("[bold red]发现的重复文件组[/bold red]")
            for idx, (hsh, paths) in enumerate(duplicates.items(), start=1):
                try:
                    size = Path(paths[0]).stat().st_size
                    size_str = format_size(size)
                except OSError:
                    size_str = "未知大小"

                group_node = tree.add(
                    f"[bold yellow]重复组 {idx}[/bold yellow] (文件大小: [green]{size_str}[/green] | 哈希: [cyan]{hsh}[/cyan])"
                )
                for p in paths:
                    group_node.add(f"[dim]{p}[/dim]")

            panel = Panel(
                tree,
                title="[bold green] 扫描完成 [/bold green]",
                subtitle=f"[bold white]共发现 {len(duplicates)} 组重复文件 | 耗时: {elapsed_time:.2f} 秒[/bold white]",
                expand=False,
            )
            console.print(panel)
        else:
            print(f"扫描完成：共发现 {len(duplicates)} 组重复文件。")
            print("==========================================")
            algo_name = "XXH3-128" if args.algorithm == "xxh3" else args.algorithm.upper()
            for hsh, paths in duplicates.items():
                print(f"\n{algo_name}: {hsh}")
                for path in paths:
                    print(f"  - {path}")
            print("==========================================")
            print(f"执行总耗时: {elapsed_time:.2f} 秒")

    if cache_file and total_files > 0:
        hit_rate = (cache_hits / total_files) * 100
        cache_msg = f"缓存统计: 命中 {cache_hits} 次 / 共 {total_files} 个文件 (避免了 {cache_hits} 次硬盘读取，命中率 {hit_rate:.1f}%)"
        if console.is_terminal:
            console.print(f"[dim]{cache_msg}[/dim]")
        else:
            print(cache_msg)

    # 写入文件输出
    if outputs:
        for out_path in outputs:
            write_results_to_file(
                out_path, duplicates, elapsed_time, total_files, includes, algorithm=args.algorithm
            )


if __name__ == "__main__":
    main()
