# Centro de Comando Meta Ads · FisioPilates

Dashboard semanal de las campañas de Meta Ads de FisioPilates (cuenta gestionada por Navarro Brand Builders).
Publicado con GitHub Pages: <https://navarro-brands.github.io/ads-dashboard-fisiopilates/>

## Páginas

| Archivo | Contenido |
|---|---|
| `index.html` | **Resumen comparativo** — pauta tradicional vs. estrategia NBB (eficiencia, participación, tendencia de la cuenta, sede por sede). |
| `tradicional.html` | **Pauta tradicional** — 12 campañas por sede. Panorama (alertas), por sede, por anuncio. Serie histórica desde el 29 jun. |
| `nbb.html` | **Estrategia NBB** — 3 campañas por audiencia × 11 sedes. Panorama, por audiencia, por sede, por anuncio. Serie desde el 31 ago. |

Todas comparten `assets/style.css`, `assets/common.js` y los datos en `assets/data.js` (generado, no editar a mano).

## Actualización semanal

1. **Exportar el CSV** de Meta Ads Manager (nivel anuncio, últimos 7 días, con columnas de campaña, conjunto, anuncio,
   clasificaciones de calidad, clics en el enlace y «Conversaciones con mensajes iniciadas») a la carpeta de CSV
   con nombre único: `NBB-Informe-<rango>.csv`. Nunca reutilizar un nombre.
2. **Tomar el alcance deduplicado** en Meta > Informes, por estrategia (filtrando campañas `CO |` y `NBB |`):
   - semanal de cada estrategia;
   - acumulado tradicional (29 jun → fin de semana) y acumulado NBB (31 ago → fin de semana).
3. En `build.py`: añadir la semana a `WEEKS` (archivo, etiqueta, fechas, `reach=dict(trad=…, nbb=…)`), actualizar
   `ACC_REACH`, `PERIODS_SHOWN` y `CUR`.
4. Redactar los comentarios en `comments.json` (claves `trad_<periodo>`, `nbb_<periodo>`, `cmp_<periodo>`;
   `draft: false` cuando estén aprobados).
5. Ejecutar:

   ```bash
   python build.py
   ```

   El script valida rollups (campañas = totales = anuncios; audiencias = sedes = conjuntos), rangos de fecha del CSV
   y que la suma de alcances semanales supere al acumulado deduplicado. Se detiene si aparece una campaña con
   nomenclatura desconocida.
6. Revisar localmente (`python -m http.server`) y hacer commit + push a `main`.

La carpeta de CSV se toma de la variable de entorno `NBB_CSV_DIR` o, por defecto, de la ruta configurada en `build.py`.
Los CSV no se versionan (`.gitignore`).

## Reglas de datos

- **Aditivas**: inversión, impresiones, conversaciones, clics → de ellas se derivan CPC, CTR, CPM, costo/conversación
  y conversaciones por cada COP 100.000.
- **No aditiva — alcance**: son personas únicas; sumar filas o semanas doble-cuenta. El alcance real solo viene de
  Meta Informes y se carga a mano. Los alcances por sede/anuncio/conjunto/audiencia se muestran como «aprox.».
  Frecuencia real = impresiones / alcance deduplicado.
- **Conversaciones** = columna «Conversaciones con mensajes iniciadas» en ambas estrategias. En las campañas NBB la
  columna «Resultados» cuenta «Clientes potenciales» (otro objetivo) y no se usa.
- **Clasificación de estrategia** por nombre de campaña: `CO | <Sede> | Ventas Whatsapp …` = tradicional;
  `NBB | <Audiencia> | Tráfico hacia WhatsApp` = NBB, con conjuntos `Sucursal <Sede> | <edad> | WA <tel>`.
  Los mapas de sedes y audiencias están en `build.py` (`TRAD_CAMPAIGNS`, `NBB_SEDES`, `NBB_AUDIENCES`).
- **Presupuestos distintos**: la comparación entre estrategias se hace sobre eficiencia (costo/conv, conv por
  COP 100.000, CTR, CPC), nunca sobre volumen absoluto.
- Se incluyen filas sin entrega/archivadas si tuvieron gasto, impresiones o resultados.
