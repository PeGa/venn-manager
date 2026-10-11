# Venn Manager

[English](README.md) · **Español**

Un libro de cuentas compartido para quienes comparten la billetera: parejas, compañeros de piso, familias. Los presupuestos planifican el mes, los movimientos registran lo que entra y sale, y una previsión te dice cuánto tendrás de verdad al terminar el mes.

Venn Manager se aloja en tu propio equipo. Funciona en un solo contenedor, guarda sus datos en un único archivo SQLite y no se conecta con nada más.

## Qué hace

- **Un solo libro para todo el hogar.** Cada miembro entra con su propia cuenta y ve el mismo dinero. Cualquier miembro puede añadir movimientos y cambiar presupuestos; los administradores gestionan las cuentas.
- **Una previsión a fin de mes en la que puedes confiar.** El Resumen muestra cuánto dinero tendrá el hogar al terminar el mes, contando todos los presupuestos. El botón **Explicar** lista cada movimiento y cada presupuesto pendiente, para que compruebes la suma tú mismo.
- **Presupuestos que planifican el mes.** Cada concepto (Alquiler, Supermercado, Sueldo…) tiene un monto con signo: negativo para el dinero que sale, positivo para el que entra. Ponle una fecha de vencimiento (una vez, semanal, cada dos semanas, mensual) y aparecerá en **Próximos** hasta que se pague.
- **Metas.** Marca un presupuesto como meta para seguir tus ahorros en su propia pantalla.
- **Registro rápido.** Escribe un monto, elige una categoría y listo. Selecciona varios movimientos con el ratón, o mantén pulsado en el móvil.
- **Historial.** Los meses pasados son de solo lectura. Búscalos, fíltralos por miembro o categoría, y mira en un gráfico circular en qué se fue el dinero.
- **Saldo.** El saldo del hogar y lo que entró y salió este mes. Si quieres, también lo que aporta cada miembro.
- **Actividad.** «Alex añadió −$84.12 a Supermercado». Haz clic en una entrada para ir a lo que cambió.
- **Los meses cambian solos.** Sin cierre de mes: el mes anterior pasa al Historial y lo que sobró se convierte en el dinero inicial de este mes.
- **Para cualquier pantalla.** Diseños ancho y estrecho, ratón y pantalla táctil, temas claro y oscuro, inglés y español.

No es un control de deudas, ni un conversor de divisas, ni un programa de contabilidad. El símbolo de moneda es una etiqueta que eliges; los montos nunca se convierten.

## Cómo se calculan los números

Cada movimiento lleva el signo que escribes: `-84.12` es dinero que sale, `2240` es dinero que entra. Cada presupuesto planifica un concepto para el mes.

```text
Previsión = dinero a inicio de mes
          + lo que los presupuestos aún esperan mover
          + lo que ya se movió este mes
```

El dinero que se mueve dentro de un presupuesto no cambia la previsión: ya estaba planificado. El dinero que lo supera reemplaza al plan. Ejemplo: planificaste −$10 para el supermercado y gastaste −$30, así que la previsión ahora cuenta −$30.

## Ponlo en marcha con Docker

Necesitas Docker con el complemento Compose.

```bash
git clone https://github.com/PeGa/venn-manager.git
cd venn-manager
sudo mkdir -p /var/lib/venn-manager
docker compose up -d --build
```

Abre `http://<tu-servidor>:8080` y entra como `admin` / `admin`. Te pedirá elegir una contraseña nueva enseguida. Después, en **Ajustes**:

1. Define el nombre del hogar, la zona horaria y el símbolo de moneda.
2. Escribe el saldo inicial: lo que el hogar tiene antes de empezar a usar Venn Manager.
3. Añade conceptos de presupuesto y fija sus montos en **Presupuesto**.
4. Invita a los demás miembros.

### Configuración

Defínelas en tu entorno o en un archivo `.env` junto a `docker-compose.yml`.

| Variable | Valor por defecto | Para qué sirve |
|---|---|---|
| `VENN_PORT` | `8080` | Puerto en el que escucha la aplicación |
| `VENN_DATA_DIR` | `/var/lib/venn-manager` | Carpeta que guarda la base de datos, `venn_manager.db` |
| `APP_ENV` | `development` | Ponlo en `production` cuando la sirvas por HTTPS, para proteger la cookie de sesión |
| `DEFAULT_ADMIN_USERNAME` | `admin` | Usuario del primer administrador; solo se usa en el primer arranque |
| `DEFAULT_ADMIN_PASSWORD` | `admin` | Contraseña del primer administrador; solo se usa en el primer arranque |
| `DEFAULT_TIMEZONE` | `UTC` | Zona horaria del hogar en el primer arranque; decide cuándo empieza y termina cada mes |

Para usarla fuera de tu red doméstica, ponla detrás de un proxy inverso con HTTPS (Caddy, nginx, Traefik…) y define `APP_ENV=production`.

### Copias de seguridad

Todo vive en un solo archivo. Detén la aplicación, copia el archivo y vuelve a arrancarla:

```bash
docker compose stop
cp /var/lib/venn-manager/venn_manager.db ~/venn_manager-$(date +%F).db
docker compose start
```

### Actualizar

```bash
git pull
docker compose up -d --build
```

Las migraciones de la base de datos se aplican solas al arrancar el contenedor. Haz una copia de seguridad antes.

## Desarrollo

Requiere Python 3.12+ y Node 24. Usa dos terminales.

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/alembic upgrade head
venv/bin/uvicorn --factory app.main:create_app --reload
```

```bash
cd frontend
npm ci
npm run dev
```

Abre http://localhost:5173. El servidor de desarrollo reenvía `/api` al backend en el puerto 8000. La configuración local está en `backend/.env`; [`docs/backend/README.md`](docs/backend/README.md) la detalla toda.

### Comprobaciones

```bash
cd backend
venv/bin/pytest
venv/bin/ruff check .
venv/bin/mypy
```

```bash
cd frontend
npm run coverage
npm run typecheck
npm run lint
```

### Hecho con

| Parte | Tecnología |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic, SQLite |
| Frontend | SolidJS, TypeScript, Vite, Tailwind CSS |
| Contenedor | nginx sirve el frontend y redirige la API, en una sola imagen |

### Dónde mirar

El comportamiento se escribe antes de construirse, en tres contratos (en inglés):

| Documento | Contenido |
|---|---|
| [`CONTRACTS/FRONTEND.md`](CONTRACTS/FRONTEND.md) | Cada pantalla e interacción |
| [`CONTRACTS/API_SURFACE.md`](CONTRACTS/API_SURFACE.md) | Cada endpoint, forma y error |
| [`CONTRACTS/BACKEND.md`](CONTRACTS/BACKEND.md) | Reglas del dominio y cada fórmula |
| [`docs/backend/README.md`](docs/backend/README.md), [`docs/frontend/README.md`](docs/frontend/README.md) | Estructura del código y cómo modificarlo |
| [`AGENTS.md`](AGENTS.md) | Reglas de código para quien contribuya, sea persona o no |

Los cambios empiezan por el contrato, luego una prueba que falla, y después el código.

## Próximamente

- Una aplicación de escritorio (Electron).

## Licencia

Copyright (C) 2026 PeGa!

Venn Manager es software libre bajo la [Licencia Pública General Affero de GNU v3.0](LICENSE) o cualquier versión posterior.

| Puedes | Debes |
|---|---|
| Usarlo, alojarlo, estudiarlo, modificarlo | Conservar los avisos de copyright y de licencia |
| Compartirlo, modificado o no | Compartir tu código fuente bajo la misma licencia |
| Ofrecer una versión modificada como servicio | Ofrecer su código fuente a quienes la usan por la red |
