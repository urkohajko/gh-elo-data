# GH-Elo

Elo propio para GreenHunter. Cubre ATP, WTA, Challenger e ITF.

## Cómo funciona

- GitHub Actions ejecuta `build_gh_elo.py` cada lunes 06:00 UTC.
- Descarga los CSV de Jeff Sackmann (2015-actualidad).
- Calcula Elo general + Elo por superficie (Hard, Clay, Grass).
- Guarda `elo_state.json` en la raíz del repo.

## Endpoint para Owen
