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
- Punto verde = overlay conectado en OBS; rojo = desconectado.

Desde un teléfono en la misma red: `http://<IP-de-la-Mac>:8777/`
(la IP aparece al ejecutar `./start.sh`).

## Prueba manual antes del servicio

1. `./start.sh` y overlay agregado en OBS.
2. Busca un versículo, pulsa **Mostrar**, verifica que se ve en OBS.
3. **Siguiente** un par de veces; verifica el fundido entre versículos.
4. **Ocultar**; verifica que la franja desaparece.
5. Reinicia el servidor y refresca la fuente en OBS; todo debe reconectar.

## Nota sobre derechos

El texto RVR1960 tiene derechos de autor (Sociedades Bíblicas Unidas). Este
repositorio no incluye ni redistribuye el texto: `data/` está fuera de git y
la descarga es para uso local de la congregación.

## Desarrollo

```bash
uv run pytest        # tests
uv run fetch-bible   # re-descargar la Biblia
```
