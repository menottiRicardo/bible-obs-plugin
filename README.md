# Biblia RVR1960 para OBS

Muestra versículos de la Reina-Valera 1960 como franja inferior (lower-third)
en OBS, controlados en vivo desde un panel web en español — desde la misma
Mac o desde un teléfono en la misma red.

## Requisitos

- macOS con [uv](https://docs.astral.sh/uv/) instalado
- OBS Studio

## Uso

```bash
./start.sh
```

Eso es todo: crea el entorno, descarga la Biblia la primera vez, arranca el
servidor y abre el panel en el navegador.

## Configurar OBS (una sola vez)

1. En la escena, agrega una fuente **Navegador** (Browser Source).
2. URL: `http://localhost:8777/overlay` — Ancho: `1920`, Alto: `1080`.
3. Listo. Cuando pulses **Mostrar** en el panel, el versículo aparece abajo.

## Panel

- **Buscar**: escribe `jn 3 16`, `1co 13:4` o `salmos 23` y pulsa **Ir**.
- **← Anterior / Siguiente →**: avanza versículo por versículo.
- **Mostrar / Ocultar**: enciende o apaga la franja sin perder la posición.
- **Mensajes**: escribe un anuncio (con línea pequeña opcional) y pulsa
  **Mostrar mensaje**, o guárdalo para reutilizarlo cada semana. Los botones
  de versículo siempre vuelven a la Biblia, sin perder la posición.
- Punto verde = overlay conectado en OBS; rojo = desconectado.

Desde un teléfono en la misma red: `http://<IP-de-la-Mac>:8777/`
(la IP aparece al ejecutar `./start.sh`).

## Desplegar en Railway (opcional)

Para controlar el panel desde cualquier lugar, no solo la red local:

1. Sube el repositorio a GitHub y crea un proyecto en [Railway](https://railway.app)
   apuntando a ese repo. Railway detecta el `Dockerfile` automáticamente.
2. En **Variables**, agrega `BIBLE_TOKEN` con un secreto largo
   (por ejemplo, el resultado de `openssl rand -hex 16`).
3. En **Settings → Networking**, genera un dominio público.
4. Reemplaza `TU-APP` y `TU_TOKEN` en estas URLs:
   - Panel: `https://TU-APP.up.railway.app/?token=TU_TOKEN`
   - Overlay para OBS: `https://TU-APP.up.railway.app/overlay?token=TU_TOKEN`

Sin `BIBLE_TOKEN` el servidor queda abierto a cualquiera: en Railway
configúralo siempre. Si el token se filtra, cámbialo en **Variables** y
actualiza las dos URLs. El uso local con `./start.sh` no cambia.

Los mensajes guardados se escriben en `data/slides.json`. En Railway el disco
se borra en cada deploy: para conservarlos, agrega un **Volume** montado en
`/data` y define la variable `BIBLE_SLIDES_PATH=/data/slides.json`. No montes
el volumen en `/app/data`: taparía la Biblia descargada dentro de la imagen.

Nota: el texto RVR1960 se descarga al construir la imagen y queda solo en tu
registro privado de Railway; no se publica en el repositorio.

## Prueba manual antes del servicio

1. `./start.sh` y overlay agregado en OBS.
2. Busca un versículo, pulsa **Mostrar**, verifica que se ve en OBS.
3. **Siguiente** un par de veces; verifica el fundido entre versículos.
4. **Ocultar**; verifica que la franja desaparece.
5. Escribe un mensaje en **Mensajes**, pulsa **Mostrar mensaje**; verifica que
   se ve en OBS y que **Siguiente** regresa al versículo.
6. Reinicia el servidor y refresca la fuente en OBS; todo debe reconectar.

## Nota sobre derechos

El texto RVR1960 tiene derechos de autor (Sociedades Bíblicas Unidas). Este
repositorio no incluye ni redistribuye el texto: `data/` está fuera de git y
la descarga es para uso local de la congregación.

## Desarrollo

```bash
uv run pytest        # tests
uv run fetch-bible   # re-descargar la Biblia
```
