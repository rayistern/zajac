#!/usr/bin/env python3
"""
main.py — CLI entry point for the Podcast Pipeline.

Usage examples:
  python main.py run                           # use RSS URL from config.yaml
  python main.py run --feed https://...rss     # override feed URL
  python main.py run --config my_config.yaml  # use a different config
  python main.py status                        # show processed episodes
  python main.py reprocess <episode-guid>      # reprocess a specific episode
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.option(
    "--config",
    default="config.yaml",
    show_default=True,
    help="Path to the YAML configuration file.",
)
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    """🎙 Podcast → Chapters → Images → Telegram Pipeline"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--feed", default=None, help="Override the RSS feed URL from config.")
@click.pass_context
def run(ctx: click.Context, feed: str | None) -> None:
    """Fetch the RSS feed and process new episodes."""
    from src.pipeline import Pipeline

    pipeline = Pipeline(config_path=ctx.obj["config"])
    pipeline.run(feed_url=feed)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show all tracked episodes and their processing status."""
    from src.config import load_config
    from src.state import StateDB

    cfg = load_config(ctx.obj["config"])
    db = StateDB(cfg["pipeline"]["state_db"])

    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT guid, title, status, processed_at, error FROM episodes ORDER BY processed_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No episodes in state database.[/yellow]")
        return

    table = Table(title="Episode Status", show_lines=True)
    table.add_column("GUID (8 chars)", style="dim")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Processed At")
    table.add_column("Error", style="red")

    STATUS_STYLES = {"done": "green", "error": "red", "processing": "yellow"}

    for row in rows:
        status_str = row["status"] or "?"
        style = STATUS_STYLES.get(status_str, "white")
        table.add_row(
            row["guid"][:8],
            row["title"] or "–",
            f"[{style}]{status_str}[/{style}]",
            row["processed_at"] or "–",
            (row["error"] or "")[:80],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# reprocess
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("guid")
@click.pass_context
def reprocess(ctx: click.Context, guid: str) -> None:
    """Force-reprocess a specific episode by its GUID (or GUID prefix)."""
    from src.config import load_config
    from src.state import StateDB

    cfg = load_config(ctx.obj["config"])
    db = StateDB(cfg["pipeline"]["state_db"])

    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM episodes WHERE guid LIKE ?", (f"{guid}%",)
    ).fetchone()
    conn.close()

    if not row:
        console.print(f"[red]No episode found with GUID starting with '{guid}'[/red]")
        sys.exit(1)

    console.print(f"[yellow]Resetting episode:[/yellow] {row['title']}")
    db.upsert_episode(row["guid"], status="pending", error=None, processed_at=None)

    from src.rss_parser import Episode
    from src.pipeline import Pipeline
    from datetime import datetime, timezone

    pub = None
    if row["published_at"]:
        try:
            pub = datetime.fromisoformat(row["published_at"])
        except ValueError:
            pass

    ep = Episode(
        guid=row["guid"],
        title=row["title"] or "",
        audio_url=row["audio_url"] or "",
        feed_url=row["feed_url"] or "",
        published_at=pub,
    )

    pipeline = Pipeline(config_path=ctx.obj["config"])
    pipeline.cfg["rss"]["force_reprocess"] = True
    pipeline.run_episode(ep)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli(obj={})
