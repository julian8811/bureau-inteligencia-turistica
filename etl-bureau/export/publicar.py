"""Publicación autónoma del ETL a GitHub. Nada levanta excepción: todo
fallo de red/git es SKIP honesto para no tumbar el daily.

Flujo: export/tableros_bureau/*.json -> bureau-inteligencia-turistica/main
-> scripts/alimentar_bureau.py en tableros-bureau -> commit+push+PR+merge.
"""
import os
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
EXPORT = BASE / "export" / "tableros_bureau"
PIEZAS = ["paises_2025_2026.json", "marca_llm_2025_2026.json",
          "informe_llm.json", "manifiesto_bureau.json"]
BIT_URL = os.environ.get("PUBLISH_BIT_URL") or "git@github.com:julian8811/bureau-inteligencia-turistica.git"
TAB_URL = os.environ.get("PUBLISH_TAB_URL") or "git@github.com:julian8811/tableros-bureau.git"
CACHE = Path(os.environ.get("PUBLISH_CACHE_DIR") or Path.home() / ".cache" / "bureau-publish")

SKIP = {"status": "skip"}


def _run(*args, **kwargs):
    return subprocess.run(list(args), capture_output=True, text=True,
                          timeout=kwargs.get("timeout", 120))


def _git(repo: Path, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                       text=True, timeout=120, env=env)
    if r.returncode != 0:
        raise RuntimeError((" ".join(args)[:60]) + ": " + (r.stderr or "")[:160])
    return r


def copiar_piezas(src: Path, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for f in PIEZAS:
        p = Path(src) / f
        if p.exists():
            (dest / f).write_bytes(p.read_bytes())
            out.append(dest / f)
    return out


def _clonar(url: str, repo: Path) -> None:
    if (repo / ".git").exists():
        _git(repo, "fetch", "origin", "main")
        return
    repo.parent.mkdir(parents=True, exist_ok=True)
    _run("git", "clone", "--depth", "1", url, str(repo))


def push_export(cache: str = "") -> dict:
    """Sube las piezas a bureau-inteligencia-turistica/main."""
    try:
        root = Path(cache) if cache else CACHE
        repo = root / "bit"
        _clonar(BIT_URL, repo)
        _git(repo, "checkout", "-B", "main", "origin/main")
        dest = repo / "etl-bureau" / "export" / "tableros_bureau"
        copiadas = copiar_piezas(EXPORT, dest)
        if not copiadas:
            return {"status": "skip", "motivo": "sin piezas"}
        _git(repo, "add", *[str(p) for p in copiadas])
        hay = _run("git", "-C", str(repo), "diff", "--cached", "--quiet")
        if hay.returncode == 0:
            return {"status": "ok", "cambios": 0}
        _git(repo, "-c", "user.name=bureau-etl", "-c",
             "user.email=bureau-etl@local", "commit", "-m",
             "data(etl): piezas tableros-bureau del daily")
        _git(repo, "push", "origin", "main")
        return {"status": "ok", "cambios": len(copiadas)}
    except Exception as e:
        print(f"[publicar][SKIP] push_export ({e})")
        return dict(SKIP)


def actualizar_tableros(cache: str = "") -> dict:
    """Corre alimentar_bureau.py + informe en tableros-bureau y mergea PR."""
    try:
        root = Path(cache) if cache else CACHE
        repo = root / "tableros"
        _clonar(TAB_URL, repo)
        _git(repo, "checkout", "-B", "publish-daily", "origin/main")
        script = repo / "scripts" / "alimentar_bureau.py"
        if script.exists():
            import sys as _sys
            r = _run(_sys.executable, str(script), timeout=300)
            if r.returncode != 0:
                print(f"[publicar][WARN] alimentar: {r.stderr[:200]}")
        inf_src = EXPORT / "informe_llm.json"
        inf_dst = repo / "data" / "open" / "informe_llm.json"
        if inf_src.exists():
            inf_dst.write_bytes(inf_src.read_bytes())
            _git(repo, "add", str(inf_dst))
        _git(repo, "add", "-A", "data/open")
        hay = _run("git", "-C", str(repo), "diff", "--cached", "--quiet")
        if hay.returncode == 0:
            return {"status": "ok", "cambios": 0}
        _git(repo, "-c", "user.name=bureau-etl", "-c",
             "user.email=bureau-etl@local", "commit", "-m",
             "data(tableros): sincroniza agregados del daily")
        try:
            _git(repo, "push", "origin", "--delete", "publish-daily")
        except Exception:
            pass
        _git(repo, "push", "-u", "origin", "publish-daily")
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        env.pop("GITHUB_TOKEN", None)
        pr = subprocess.run(["gh", "pr", "create", "--repo", "julian8811/tableros-bureau",
                             "--head", "publish-daily", "--base", "main",
                             "--title", "Datos diarios del ETL",
                             "--body", "Sincronización automática del daily."],
                            capture_output=True, text=True, timeout=60, env=env,
                            cwd=str(repo))
        if pr.returncode != 0 and "already exists" not in (pr.stderr or ""):
            raise RuntimeError("gh pr create: " + (pr.stderr or "")[:160])
        mg = subprocess.run(["gh", "pr", "merge", "--repo", "julian8811/tableros-bureau",
                             "publish-daily", "--merge"], capture_output=True,
                            text=True, timeout=60, env=env, cwd=str(repo))
        if mg.returncode != 0:
            raise RuntimeError("gh pr merge: " + (mg.stderr or "")[:160])
        try:
            _git(repo, "push", "origin", "--delete", "publish-daily")
        except Exception:
            pass
        return {"status": "ok", "cambios": 1}
    except Exception as e:
        print(f"[publicar][SKIP] actualizar_tableros ({e})")
        return dict(SKIP)


if __name__ == "__main__":
    print(push_export())
    print(actualizar_tableros())
