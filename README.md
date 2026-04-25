# planetslifeposibility

Backend en **Python + FastAPI** que genera **sistemas solares** de forma procedural, evalúa **habitabilidad** al estilo Tierra, y simula en **fast-forward** (millones de años) el surgimiento de **civilizaciones** con puntuaciones de tecnología, disposición (hostil ↔ pacifista) y extinción, entre otra metadata pensada para juegos, demos o análisis lúdicos.

> **Importante:** no es un simulador físico riguroso. Los valores son **scores y heurísticas** (temperatura, agua, atmósfera, zona habitable, etc.), no predicciones científicas.

---

## Qué hace el proyecto

1. **Sistemas y estrellas**  
   Genera estrellas con clase espectral aproximada (M, K, G, F), luminosidad y **zona habitable** en UA, y un conjunto de planetas con órbita, masa, temperatura y parámetros “tipo Tierra”.

2. **Habitabilidad y vida (pre-simulación)**  
   Calcula un **índice de habitabilidad** (0–100) y un **nivel de vida** biótica: desde ninguna hasta biomas complejos, en función de agua, temperatura, presión, oxígeno, campo magnético y química orgánica simplificada.

3. **Simulación temporal (fast-forward)**  
   En una ventana de **millones de años** a tu elección, decide si surge **vida inteligente**, evolución tecnológica, posibles **extinciones** civilizatorias, logros de **tecnología avanzada** (umbral configurable) y, a escala de sistema, si aparece un **imperio multiplanetario** o explotación de recursos a escala planetaria o estelar (siempre como scores).

4. **Civilizaciones (scores)**  
   Cada cultura (por planeta con inteligencia) puede incluir: tecnología 0–100, era nominal (piedra, medieval, industrial, espacio, hipertecnología, etc.), hipertecnología, disposición hostil/pacifista, eventos de “salto” anacrónico, y causas de extinción si aplica.

5. **Registro en memoria**  
   Tras simular, se pueden listar entradas en **`GET /civilizations`** con filtros (mínima tecnología, extintas, multiplaneta, hipertecnológicas). Los datos **no se persisten en disco**; al reiniciar el servidor se pierden.

---

## Requisitos

- Python 3.10+ (recomendado 3.11+)

## Instalación y arranque

```bash
cd planets
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Linux / macOS:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Documentación interactiva (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Si en Windows aparece un error de permisos con el **puerto 8000** (`WinError 10013`), prueba otro puerto, por ejemplo:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

y abre `http://127.0.0.1:8001/docs`.

---

## API (resumen)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/systems/generate` | Genera un sistema y lo guarda en memoria |
| `GET` | `/systems` | Lista sistemas guardados |
| `GET` | `/systems/{id}` | Detalle de un sistema |
| `POST` | `/simulation/batch` | Genera *N* sistemas en secuencia y simula con el mismo avance en millones de años |
| `POST` | `/simulation/system/{id}` | Simula un sistema ya guardado |
| `GET` | `/civilizations` | Lista civilizaciones registradas (query: `min_technology`, `extinct_only`, etc.) |
| `GET` | `/technology/eras` | Catálogo de etapas tecnológicas y rangos de score |

**Ejemplo mínimo** (`POST /simulation/batch`): genera 3 sistemas, avanza 2000 millones de años en cada uno y devuelve `generation_base_seed` para reproducir el lote con la misma semilla.

```json
{
  "system_count": 3,
  "seed": 12345,
  "min_planets": 4,
  "max_planets": 8,
  "name_prefix": "Cluster",
  "advance_million_years": 2000,
  "advanced_technology_threshold": 80
}
```

---

## Estructura del código

```
app/
  main.py         # Rutas FastAPI
  generator.py   # Procedural de sistemas y planetas
  life.py         # Habitabilidad y niveles de vida
  simulation.py  # Fast-forward, civilizaciones, extinción, multiplaneta
  tech_eras.py   # Mapeo score → etapa (piedra, medieval, etc.)
  civ_registry.py# Registro en memoria de civilizaciones
  schemas.py     # Modelos Pydantic
  store.py        # Almacén en memoria de sistemas
  config.py
requirements.txt
```

---

## Licencia

Sin licencia explícita en el repositorio: añade un archivo `LICENSE` si quieres condiciones claras de uso.
