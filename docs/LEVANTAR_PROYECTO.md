# Cómo levantar el proyecto

Guía rápida para ver la aplicación en el navegador. El detalle completo está en `README.md` (sección de entorno y ejecución).

## Stack

- Backend: Flask 3.1.3 (Python 3.11 o 3.13) en `backend/`, fábrica `backend:create_app`.
- Frontend: React 19 + Vite 8 en `frontend/`; Vite hace proxy de `/api` a Flask.
- Base: SQLite en `%LOCALAPPDATA%\TP-DAO\tp_dao.db` (se cambia con la variable `TP_DAO_DB`).

## Requisitos (ya instalados en este equipo)

- `.venv` en la raíz con Flask y pytest. Si falta:
  ```powershell
  py -3.11 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
  ```
  `py -0` lista las versiones instaladas; si no está la 3.11, usar la disponible (por ejemplo `py -3.13`).
- `frontend/node_modules`. Si falta: `cd frontend; npm.cmd install`.
- Node `^20.19.0 || >=22.12.0` (instalado: 22.14.0).

Usar `npm.cmd` en vez de `npm` (PowerShell bloquea `npm.ps1`) y `.\.venv\Scripts\python.exe` en vez de `python` (apunta al alias de Microsoft Store).

## Modo desarrollo (dos terminales, desde la raíz del repo)

Terminal 1 — backend en el puerto 5000:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app --no-debug run --host 127.0.0.1 --port 5000 --no-reload
```

Terminal 2 — frontend en el puerto 5173:

```powershell
cd frontend
npm.cmd run dev
```

Abrir http://127.0.0.1:5173/

## Modo build servido por Flask (un solo servidor)

```powershell
cd frontend; npm.cmd run build; cd ..
.\.venv\Scripts\python.exe -m flask --app backend:create_app --no-debug run --host 127.0.0.1 --port 5000 --no-reload
```

Abrir http://127.0.0.1:5000/

## Comprobación

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health   # {"status":"ok"}
Invoke-RestMethod http://127.0.0.1:5173/api/health   # mismo resultado, vía proxy Vite
```

## Notas

- Antes de levantar, comprobar que los puertos estén libres: `netstat -ano | findstr ":5000 :5173"`. Vite usa puerto estricto: si 5173 está ocupado, falla en vez de elegir otro.
- Flask no falla si ya hay otra instancia en el 5000: en Windows arranca igual, y dos procesos sobre la misma base no deben convivir. Comprobar que no quede ninguno con `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -like '*flask*'`.
- Para cambiar puertos: copiar `frontend/.env.example` a `frontend/.env.local` (`FRONTEND_PORT`, `API_PROXY_TARGET`) y usar el mismo puerto en `--port` de Flask.
- Para probar con datos vacíos sin tocar la base real: `$env:TP_DAO_DB = "$env:TEMP\tp_prueba.db"` antes de iniciar Flask.
- Detener cada servidor con Ctrl+C (si `npm.cmd` pregunta, responder `S`).
- Tests: `.\.venv\Scripts\python.exe -m pytest -q` (la suite completa tarda entre 4 y 5 minutos en el equipo de F-07.2; en el equipo original llegó a 48 minutos).
