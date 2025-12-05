#!/usr/bin/env python3
"""
RedFin RSS Management CLI

사용법:
    python -m backend.cli.main init-db
    python -m backend.cli.main sync-feeds --delete-missing
    python -m backend.cli.main update-feeds --days 7
    python -m backend.cli.main discover --url https://example.com --top-k 3
    python -m backend.cli.main stats --days 7 --out data/stats.json
"""
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from backend.core.config import DISCOVER_TARGETS, PROJECT_ROOT
from backend.core.container import Container
from backend.core.database import MongoManager
from backend.repositories import EntryRepository, FeedRepository

# Note: CLI는 Container를 통해 서비스를 생성하므로 API 계층을 의존하지 않습니다.

app = typer.Typer(help="RedFin RSS Management CLI")
console = Console()


@app.callback()
def callback():
    """RedFin RSS Manager CLI"""
    pass


@app.command("init-db")
def init_db():
    """MongoDB 인덱스 생성 및 초기화"""
    console.print("[bold blue]MongoDB 인덱스 초기화 시작...[/bold blue]")
    
    try:
        # MongoDB 연결 확인
        MongoManager.get_client().admin.command('ping')
        console.print("[green]✓[/green] MongoDB 연결 성공")
        
        # EntryRepository 인덱스 생성
        console.print("[yellow]entries 컬렉션 인덱스 생성 중...[/yellow]")
        entry_repo = EntryRepository()
        entry_repo.create_indexes()
        console.print("[green]✓[/green] entries 컬렉션 인덱스 생성 완료")
        
        # FeedRepository 인덱스 생성
        console.print("[yellow]feeds 컬렉션 인덱스 생성 중...[/yellow]")
        feed_repo = FeedRepository()
        feed_repo.create_indexes()
        console.print("[green]✓[/green] feeds 컬렉션 인덱스 생성 완료")
        
        console.print("[bold green]✓ 모든 인덱스 초기화 완료[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ 인덱스 초기화 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("init")
def init_feeds():
    """MongoDB에서 활성화된 피드를 Reader에 등록하고 업데이트"""
    console.print("[bold blue]피드 초기화 시작...[/bold blue]")
    
    try:
        crawler = Container.get_crawler_service()
        result = crawler.init_feeds()
        
        console.print(f"[green]✓[/green] 추가: {result['added']}개")
        console.print(f"[yellow]⊘[/yellow] 건너뜀: {result['skipped']}개")
        console.print(f"[cyan]⏱[/cyan] 소요 시간: {result['update_sec']}초")
        console.print(f"[bold green]✓ 피드 초기화 완료[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ 피드 초기화 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("update-feeds")
def update_feeds(days: int = typer.Option(1, "--days", "-d", help="업데이트할 일수 (0=전체)")):
    """RSS 피드 수집 및 업데이트"""
    console.print(f"[bold blue]피드 업데이트 시작 (days={days})...[/bold blue]")
    
    try:
        crawler = Container.get_crawler_service()
        days_param = None if days == 0 else days
        result = crawler.update_all(days=days_param)
        
        console.print(f"[green]✓[/green] 업데이트 완료")
        console.print(f"[cyan]⏱[/cyan] 소요 시간: {result['update_sec']}초")
        if 'mongo_entries' in result:
            entries = result['mongo_entries'].get('entries_processed', 0)
            console.print(f"[green]✓[/green] 처리된 엔트리: {entries}개")
        
    except Exception as e:
        console.print(f"[bold red]✗ 피드 업데이트 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("discover")
def discover(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="탐색할 URL"),
    top_k: int = typer.Option(3, "--top-k", "-k", help="최대 후보 수")
):
    """URL에서 RSS 피드 발견 및 추가"""
    feed_service = Container.get_feed_service()
    
    if url:
        console.print(f"[bold blue]피드 발견 중: {url}...[/bold blue]")
        result = feed_service.discover_feeds(url, top_k=top_k)
    else:
        console.print(f"[bold blue]기본 타깃 URL에서 피드 발견 중...[/bold blue]")
        results = []
        for target_url in DISCOVER_TARGETS:
            result = feed_service.discover_feeds(target_url, top_k=top_k)
            results.append(result)
        result = {"results": results}
    
    console.print(f"[green]✓[/green] 발견: {result.get('added', 0)}개")
    console.print(f"[yellow]⊘[/yellow] 건너뜀: {result.get('skipped', 0)}개")
    if 'candidates' in result:
        console.print(f"[cyan]후보:[/cyan] {', '.join(result['candidates'])}")


@app.command("stats")
def stats(
    days: int = typer.Option(7, "--days", "-d", help="통계 기간 (일)"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="출력 파일 경로")
):
    """통계 조회"""
    console.print(f"[bold blue]통계 조회 중 (최근 {days}일)...[/bold blue]")
    
    try:
        crawler = Container.get_crawler_service()
        result = crawler.get_stats(days=days)
        
        # 테이블로 표시
        table = Table(title=f"RSS 통계 (최근 {days}일)")
        table.add_column("항목", style="cyan")
        table.add_column("값", style="green")
        
        table.add_row("총 피드", str(result['feeds']))
        table.add_row("총 엔트리", str(result['entries_total']))
        table.add_row("최근 엔트리", str(result['entries_recent']))
        
        console.print(table)
        
        # 파일로 저장
        if out:
            output_path = Path(out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            console.print(f"[green]✓[/green] 통계 저장: {out}")
        else:
            console.print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            
    except Exception as e:
        console.print(f"[bold red]✗ 통계 조회 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("sync-feeds")
def sync_feeds(
    delete_missing: bool = typer.Option(False, "--delete-missing", help="소스에 없는 피드 제거")
):
    """feeds.yaml 및 OPML 파일과 DB 동기화"""
    console.print("[bold blue]피드 동기화 시작...[/bold blue]")
    
    try:
        feed_service = Container.get_feed_service()
        result = feed_service.sync_feeds_to_mongo(delete_missing=delete_missing)
        
        console.print(f"[green]✓[/green] 추가: {result['added']}개")
        console.print(f"[yellow]⊘[/yellow] 수정: {result['modified']}개")
        if delete_missing:
            console.print(f"[red]✗[/red] 삭제: {result['deleted']}개")
        console.print(f"[cyan]⊘[/cyan] 유지: {result['kept']}개")
        console.print(f"[bold green]✓ 피드 동기화 완료[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ 피드 동기화 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("import-opml")
def import_opml(
    file: str = typer.Argument(..., help="OPML 파일 경로"),
    mirror: bool = typer.Option(True, "--mirror/--no-mirror", help="MongoDB로 미러링")
):
    """OPML 파일에서 피드 가져오기"""
    console.print(f"[bold blue]OPML 가져오기: {file}...[/bold blue]")
    
    try:
        feed_service = Container.get_feed_service()
        file_path = Path(file)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path
        
        blacklist = feed_service.load_blacklist_urls()
        result = feed_service.import_opml(file_path, blacklist=blacklist)
        
        console.print(f"[green]✓[/green] 추가: {result['added']}개")
        console.print(f"[yellow]⊘[/yellow] 건너뜀: {result['skipped']}개")
        
        if mirror:
            crawler = Container.get_crawler_service()
            mongo_result = crawler.mirror_feeds_to_mongo()
            console.print(f"[green]✓[/green] MongoDB 미러링 완료")
        
    except Exception as e:
        console.print(f"[bold red]✗ OPML 가져오기 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("export-opml")
def export_opml(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="출력 파일 경로")
):
    """현재 Reader 피드를 OPML로 내보내기"""
    console.print("[bold blue]OPML 내보내기...[/bold blue]")
    
    try:
        feed_service = Container.get_feed_service()
        xml = feed_service.export_opml()
        
        if output:
            output_path = Path(output)
            if not output_path.is_absolute():
                output_path = PROJECT_ROOT / output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(xml, encoding="utf-8")
            console.print(f"[green]✓[/green] OPML 저장: {output_path}")
        else:
            console.print(xml)
            
    except Exception as e:
        console.print(f"[bold red]✗ OPML 내보내기 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("sync-yaml")
def sync_yaml(
    delete_missing: bool = typer.Option(False, "--delete-missing", help="소스에 없는 피드 제거")
):
    """feeds.yaml ↔ Reader 동기화"""
    console.print("[bold blue]YAML 동기화 시작...[/bold blue]")
    
    try:
        feed_service = Container.get_feed_service()
        result = feed_service.sync_from_yaml(delete_missing=delete_missing)
        
        console.print(f"[green]✓[/green] 추가: {result['added']}개")
        if delete_missing:
            console.print(f"[red]✗[/red] 제거: {result['removed']}개")
        console.print(f"[cyan]⊘[/cyan] 유지: {result['kept']}개")
        console.print(f"[bold green]✓ YAML 동기화 완료[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ YAML 동기화 실패: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

