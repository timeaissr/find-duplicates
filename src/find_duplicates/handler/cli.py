import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import load_json_report, validate_selections, recycle_files

console = Console()

def format_size(size_in_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def run_cli_handler(report_path: str) -> None:
    path = Path(report_path)
    if not path.is_file():
        console.print(f"[bold red]错误: 报告文件 '{report_path}' 不存在。[/bold red]", style="red")
        sys.exit(1)

    try:
        summary, duplicates = load_json_report(path)
    except Exception as e:
        console.print(f"[bold red]解析 JSON 报告失败: {e}[/bold red]")
        sys.exit(1)

    if not duplicates:
        console.print("[bold green]报告中没有重复文件记录。无需处理。[/bold green]")
        return

    keep_paths = set()
    trash_paths = set()

    console.print(Panel("[bold green]进入 重复文件命令行交互处理器 (CLI)[/bold green]", expand=False))
    console.print("操作说明: 输入序号保留指定文件，其余自动回收。输入 's' 跳过，输入 'q' 退出。\n")

    # 循环遍历组
    for idx, (hsh, paths) in enumerate(duplicates.items(), start=1):
        console.print(f"[bold yellow]重复组 {idx}/{len(duplicates)}[/bold yellow] (Hash: {hsh})")
        table = Table(title="备选文件列表", show_header=True, header_style="bold magenta")
        table.add_column("序号", style="dim", width=6)
        table.add_column("修改时间", width=20)
        table.add_column("文件大小", width=12)
        table.add_column("文件路径")

        valid_paths = []
        for file_idx, p_str in enumerate(paths, start=1):
            p = Path(p_str)
            if not p.is_file():
                continue
            valid_paths.append(p_str)
            stat = p.stat()
            from datetime import datetime
            mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size_str = format_size(stat.st_size)
            table.add_row(str(file_idx), mtime_str, size_str, p_str)

        if not valid_paths:
            console.print("[red]当前组文件在磁盘上已全部不存在。[/red]\n")
            continue

        console.print(table)

        while True:
            choice = input("请输入要【保留】的序号 (s:跳过, q:退出): ").strip().lower()
            if choice == "q":
                console.print("[yellow]操作被终止。[/yellow]")
                sys.exit(0)
            elif choice == "s":
                console.print("[dim]已跳过当前组[/dim]\n")
                break
            elif choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(valid_paths):
                    keep_file = valid_paths[val - 1]
                    keep_paths.add(keep_file)
                    for other in valid_paths:
                        if other != keep_file:
                            trash_paths.add(other)
                    console.print(f"[green]已选择保留: {keep_file}，其余移至待回收[/green]\n")
                    break
            console.print("[red]输入无效，请输入正确的序号、's' 或 'q'。[/red]")

    if not trash_paths:
        console.print("[yellow]没有文件被标记为回收。[/yellow]")
        return

    # 安全检查
    err = validate_selections(duplicates, keep_paths, trash_paths)
    if err:
        console.print(f"[bold red]{err}[/bold red]")
        sys.exit(1)

    # 汇总展示并最终确认
    console.print(Panel("[bold yellow]待回收文件确认清单[/bold yellow]", expand=False))
    total_size_to_recycle = 0
    for p_str in sorted(trash_paths):
        p = Path(p_str)
        if p.is_file():
            size = p.stat().st_size
            total_size_to_recycle += size
            console.print(f"  [red]🗑️  [回收][/red] {p_str} ({format_size(size)})")

    console.print(f"\n共准备回收 [red]{len(trash_paths)}[/red] 个重复文件，预计释放 [green]{format_size(total_size_to_recycle)}[/green] 空间。")
    confirm = input("确认将上述文件移至回收站吗？(y/n): ").strip().lower()
    if confirm == "y":
        count, reclaimed = recycle_files(list(trash_paths))
        console.print(f"[bold green]成功移入回收站！共回收了 {count} 个文件，实际释放空间: {format_size(reclaimed)}[/bold green]")
    else:
        console.print("[yellow]操作已取消。[/yellow]")
