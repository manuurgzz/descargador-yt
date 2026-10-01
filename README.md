# Descargador YT

App con ventana para descargar vídeos (o solo el audio) de YouTube a partir de la URL.

App para Windows 10/11.

## Primera vez
1. Descarga el proyecto: botón verde **Code → Download ZIP** (o la última versión en **Releases**) y descomprímelo.
2. Doble clic en **INSTALAR.bat**. Instala Python si falta, actualiza yt-dlp y añade ffmpeg y Deno si faltan (YouTube exige un motor de JavaScript para algunos formatos).

Si tienes también **Reddit Video** en una carpeta al lado (`…\Reddit Video`), la lista de destinos muestra sus carpetas de fondos.

## Uso
Doble clic en **Descargador YT.bat** y:
1. Pega una o varias URLs, una por línea.
2. Elige el formato:
   - **MP4 1080p compatible**: se abre en cualquier reproductor.
   - **Máxima calidad**: 4K si existe.
   - **1080p sin audio**: para fondos.
   - **Solo audio MP3**.
3. Elige dónde guardar. En la lista salen `descargas` y las carpetas de `Reddit Video\fondos`, para que el clip vaya directo al generador. Al elegir una carpeta de fondos, el formato cambia solo a «sin audio».
4. Opcional: recorta con **desde / hasta** (mm:ss) para bajar solo un trozo.

## Si deja de funcionar
YouTube cambia a menudo y yt-dlp se actualiza para seguirle el ritmo. Si una descarga falla, ejecuta **INSTALAR.bat** otra vez.

## Ojo con los derechos
Descarga solo vídeos que tengas derecho a usar: los tuyos, los que tienen licencia Creative Commons o los que tienen permiso del autor. Si subes a YouTube o TikTok material ajeno, te pueden llegar reclamaciones de copyright o bloqueos del vídeo.
