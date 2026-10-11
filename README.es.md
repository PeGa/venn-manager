# Venn Manager

[English](README.md) · **Español**

Un libro de cuentas compartido para los que comparten la billetera: parejas, compañeros de depto, familias. Los presupuestos planifican el mes, los movimientos registran lo que entra y sale, y una previsión te dice cuánto vas a tener de verdad cuando termine el mes.

Venn Manager se instala en tu propia computadora o servidor. Corre en un solo contenedor, guarda sus datos en un único archivo SQLite y no se conecta con nada más.

## Qué hace

- **Un solo libro para todo el hogar.** Cada miembro entra con su propia cuenta y ve la misma plata. Cualquier miembro puede agregar movimientos y cambiar presupuestos; los administradores manejan las cuentas.
- **Una previsión a fin de mes en la que podés confiar.** El Resumen muestra cuánta plata va a tener el hogar cuando termine el mes, contando todos los presupuestos. El botón **Explicar** lista cada movimiento y cada presupuesto pendiente, así comprobás la cuenta vos mismo.
- **Presupuestos que planifican el mes.** Cada concepto (Alquiler, Supermercado, Sueldo…) tiene un monto con signo: negativo para la plata que sale, positivo para la que entra. Ponele una fecha de vencimiento (una vez, semanal, cada dos semanas, mensual) y va a aparecer en **Próximos** hasta que se pague.
- **Metas.** Marcá un presupuesto como meta para seguir tus ahorros en su propia pantalla.
- **Carga rápida.** Escribí un monto, elegí una categoría y listo. Seleccioná varios movimientos con el mouse, o mantené apretado en el celular.
- **Historial.** Los meses pasados son de solo lectura. Buscalos, filtralos por miembro o categoría, y mirá en un gráfico de torta en qué se fue la plata.
- **Saldo.** El saldo del hogar y lo que entró y salió este mes. Si querés, también lo que aporta cada miembro.
- **Actividad.** «Alex añadió −$84.12 a Supermercado». Hacé clic en una entrada para ir a lo que cambió.
- **Los meses cambian solos.** No hay cierre de mes: el mes anterior pasa al Historial y lo que sobró se convierte en la plata inicial de este mes.
- **Para cualquier pantalla.** Diseño ancho y angosto, mouse y pantalla táctil, temas claro y oscuro, inglés y español.

No es un control de deudas, ni un conversor de monedas, ni un programa de contabilidad. El símbolo de moneda es una etiqueta que elegís vos; los montos nunca se convierten.

## Cómo se calculan los números

Cada movimiento lleva el signo que escribís: `-84.12` es plata que sale, `2240` es plata que entra. Cada presupuesto planifica un concepto para el mes.

```text
Previsión = plata a inicio de mes
          + lo que los presupuestos todavía esperan mover
          + lo que ya se movió este mes
```

La plata que se mueve dentro de un presupuesto no cambia la previsión: ya estaba planificada. La que lo supera reemplaza al plan. Por ejemplo: planificaste −$10 para el súper y gastaste −$30, así que ahora la previsión cuenta −$30.

## Levantalo con Docker

Necesitás Docker con el plugin de Compose.

```bash
git clone https://github.com/PeGa/venn-manager.git
cd venn-manager
sudo mkdir -p /var/lib/venn-manager
docker compose up -d --build
```

Abrí `http://<tu-servidor>:8080` y entrá como `admin` / `admin`. Te va a pedir que elijas una contraseña nueva de entrada. Después, en **Ajustes**:

1. Poné el nombre del hogar, la zona horaria y el símbolo de moneda.
2. Cargá el saldo inicial: lo que tiene el hogar antes de empezar a usar Venn Manager.
3. Agregá los conceptos de presupuesto y poneles el monto en **Presupuesto**.
4. Invitá al resto de los miembros.

### Configuración

Definilas en tu entorno o en un archivo `.env` al lado de `docker-compose.yml`.

| Variable | Valor por defecto | Para qué sirve |
|---|---|---|
| `VENN_PORT` | `8080` | Puerto en el que escucha la app |
| `VENN_DATA_DIR` | `/var/lib/venn-manager` | Carpeta donde vive la base de datos, `venn_manager.db` |
| `APP_ENV` | `development` | Ponelo en `production` cuando la sirvas por HTTPS, para proteger la cookie de sesión |
| `DEFAULT_ADMIN_USERNAME` | `admin` | Usuario del primer administrador; solo se usa en el primer arranque |
| `DEFAULT_ADMIN_PASSWORD` | `admin` | Contraseña del primer administrador; solo se usa en el primer arranque |
| `DEFAULT_TIMEZONE` | `UTC` | Zona horaria del hogar en el primer arranque; define cuándo empieza y termina cada mes |

Para usarla fuera de tu red de casa, ponela detrás de un proxy inverso con HTTPS (Caddy, nginx, Traefik…) y definí `APP_ENV=production`.

### Backup

Todo vive en un solo archivo. Pará la app, copiá el archivo y volvé a levantarla:

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

Las migraciones de la base de datos se aplican solas cuando arranca el contenedor. Hacé un backup antes.

## Desarrollo

Necesitás Python 3.12+ y Node 24. Usá dos terminales.

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

Abrí http://localhost:5173. El servidor de desarrollo redirige `/api` al backend en el puerto 8000. La configuración local está en `backend/.env`; [`docs/backend/README.md`](docs/backend/README.md) la detalla toda.

### Chequeos

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

El comportamiento se escribe antes de programarse, en tres contratos (en inglés):

| Documento | Qué cubre |
|---|---|
| [`CONTRACTS/FRONTEND.md`](CONTRACTS/FRONTEND.md) | Cada pantalla e interacción |
| [`CONTRACTS/API_SURFACE.md`](CONTRACTS/API_SURFACE.md) | Cada endpoint, forma y error |
| [`CONTRACTS/BACKEND.md`](CONTRACTS/BACKEND.md) | Reglas del dominio y cada fórmula |
| [`docs/backend/README.md`](docs/backend/README.md), [`docs/frontend/README.md`](docs/frontend/README.md) | Cómo está organizado el código y cómo cambiarlo |
| [`AGENTS.md`](AGENTS.md) | Reglas de código para quien contribuya, persona o no |

Los cambios arrancan por el contrato, después una prueba que falla, y recién ahí el código.

## Próximamente

- Una app de escritorio (Electron).

## Licencia

Copyright (C) 2026 PeGa!

Venn Manager es software libre bajo la [Licencia Pública General Affero de GNU v3.0](LICENSE) o cualquier versión posterior. Todas las versiones anteriores en el historial de este repositorio también están disponibles bajo AGPL-3.0-or-later.

| Podés | Tenés que |
|---|---|
| Usarlo, instalarlo en tu servidor, estudiarlo, modificarlo | Mantener los avisos de copyright y de licencia |
| Compartirlo, modificado o no | Compartir tu código fuente bajo la misma licencia |
| Ofrecer una versión modificada como servicio | Ofrecerles el código fuente a los que la usan por la red |
