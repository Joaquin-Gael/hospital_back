"""Script para sincronizar valores de enums de auditoría con PostgreSQL.

Este script debe ejecutarse cuando:
- Se agregan nuevos valores a los enums en taxonomy.py
- Después de restaurar una base de datos
- En el despliegue inicial
"""

from sqlmodel import Session, create_engine
from rich.console import Console
from rich.panel import Panel

from app.audit.enum_utils import (
    AUDIT_ENUM_DEFINITIONS,
    build_sync_plan,
    missing_statements,
)
from app.config import db_url


console = Console()


def sync_audit_enums() -> None:
    """Sincroniza todos los enums de auditoría con la base de datos."""
    
    console.print("\n[bold cyan]🔄 Sincronizando enums de auditoría...[/bold cyan]\n")
    
    try:
        engine = create_engine(db_url)
        
        with Session(engine) as session:
            # Construir plan de sincronización
            states = build_sync_plan(session, AUDIT_ENUM_DEFINITIONS)
            
            # Obtener sentencias SQL necesarias
            statements = missing_statements(states)
            
            if not statements:
                console.print(
                    Panel.fit(
                        "[green]✓ Todos los enums de auditoría están actualizados[/green]",
                        border_style="green",
                        padding=(1, 2)
                    )
                )
                return
            
            # Mostrar valores que se agregarán
            console.print(f"[yellow]Se agregarán {len(statements)} nuevos valores:[/yellow]\n")
            for stmt in statements:
                console.print(f"  [dim]→[/dim] {stmt}")
            
            console.print()
            
            # Ejecutar las sentencias
            for stmt in statements:
                try:
                    session.exec(stmt)
                    console.print(f"  [green]✓[/green] Ejecutado: [dim]{stmt}[/dim]")
                except Exception as e:
                    console.print(f"  [red]✗[/red] Error: {e}")
                    raise
            
            session.commit()
            
            console.print(
                Panel.fit(
                    "[bold green]✓ Enums sincronizados exitosamente[/bold green]",
                    border_style="bright_green",
                    padding=(1, 2)
                )
            )
            
    except Exception as e:
        console.print(
            Panel.fit(
                f"[bold red]✗ Error al sincronizar enums:[/bold red]\n\n{str(e)}",
                border_style="red",
                padding=(1, 2)
            )
        )
        raise


if __name__ == "__main__":
    sync_audit_enums()