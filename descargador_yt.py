#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descargador YT — descarga vídeos (o solo audio) de YouTube a partir de la URL.

· Pega una o varias URLs (una por línea) y pulsa Descargar.
· Formatos: MP4 1080p compatible, máxima calidad (4K si existe) o solo audio MP3.
· Recorte opcional (desde / hasta) para quedarte solo con un trozo.
· Destino: carpeta de descargas o directamente una carpeta de fondos del generador de vídeos.

Usa yt-dlp + ffmpeg. Descarga solo contenido que tengas derecho a usar.
"""

import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

BASE = Path(__file__).resolve().parent
CARPETA_DESCARGAS = BASE / "descargas"
CARPETA_FONDOS = BASE.parent / "Reddit Video" / "fondos"  # app hermana en AppsLocal

FORMATOS = {
    "Vídeo MP4 1080p (compatible)": {
        "format": "bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
    },
    "Vídeo máxima calidad (4K si hay)": {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
    },
    "Vídeo MP4 1080p SIN audio (fondos)": {
        "format": "bv*[vcodec^=avc1][height<=1080]/bv*[height<=1080]/b",
    },
    "Solo audio MP3": {
        "format": "ba/b",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    },
}


def buscar_ffmpeg():
    """Devuelve la carpeta de ffmpeg (también si se instaló con winget y el PATH no se ha refrescado)."""
    p = shutil.which("ffmpeg")
    if p:
        return str(Path(p).parent)
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    enlace = local / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
    if enlace.exists():
        return str(enlace.parent)
    for exe in (local / "Microsoft" / "WinGet" / "Packages").glob("Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"):
        return str(exe.parent)
    return None


def a_segundos(texto):
    """'1:23', '01:02:03' o '83' -> segundos. Vacío -> None."""
    texto = texto.strip()
    if not texto:
        return None
    if not re.fullmatch(r"\d+(:\d{1,2}){0,2}(\.\d+)?", texto):
        raise ValueError(f"Tiempo no válido: {texto!r} (usa mm:ss)")
    s = 0.0
    for parte in texto.split(":"):
        s = s * 60 + float(parte)
    return s


def destinos_disponibles():
    opciones = [str(CARPETA_DESCARGAS)]
    if CARPETA_FONDOS.is_dir():
        opciones += [str(d) for d in sorted(CARPETA_FONDOS.iterdir()) if d.is_dir()]
    return opciones


class App:
    def __init__(self, root):
        self.root = root
        self.cola = queue.Queue()
        self.trabajando = False
        root.title("Descargador YT")
        root.geometry("720x560")
        root.minsize(620, 480)

        estilo = ttk.Style()
        try:
            estilo.theme_use("vista" if sys.platform == "win32" else "clam")
        except tk.TclError:
            pass

        m = ttk.Frame(root, padding=14)
        m.pack(fill="both", expand=True)

        ttk.Label(m, text="URLs de YouTube (una por línea):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.urls = tk.Text(m, height=6, wrap="none", font=("Consolas", 10))
        self.urls.pack(fill="x", pady=(4, 10))
        self.urls.bind("<Control-v>", self._pegar)

        fila = ttk.Frame(m)
        fila.pack(fill="x", pady=4)
        ttk.Label(fila, text="Formato:", width=10).pack(side="left")
        self.formato = ttk.Combobox(fila, values=list(FORMATOS), state="readonly", width=38)
        self.formato.current(0)
        self.formato.pack(side="left")

        fila = ttk.Frame(m)
        fila.pack(fill="x", pady=4)
        ttk.Label(fila, text="Guardar en:", width=10).pack(side="left")
        self.destino = ttk.Combobox(fila, values=destinos_disponibles())
        self.destino.set(str(CARPETA_DESCARGAS))
        self.destino.pack(side="left", fill="x", expand=True)
        ttk.Button(fila, text="Elegir…", command=self._elegir).pack(side="left", padx=(6, 0))

        fila = ttk.Frame(m)
        fila.pack(fill="x", pady=4)
        ttk.Label(fila, text="Recortar:", width=10).pack(side="left")
        ttk.Label(fila, text="desde").pack(side="left")
        self.desde = ttk.Entry(fila, width=8)
        self.desde.pack(side="left", padx=4)
        ttk.Label(fila, text="hasta").pack(side="left")
        self.hasta = ttk.Entry(fila, width=8)
        self.hasta.pack(side="left", padx=4)
        ttk.Label(fila, text="(mm:ss, opcional — vacío = vídeo entero)", foreground="#777").pack(side="left", padx=6)

        fila = ttk.Frame(m)
        fila.pack(fill="x", pady=(10, 4))
        self.boton = ttk.Button(fila, text="⬇  Descargar", command=self.empezar)
        self.boton.pack(side="left")
        ttk.Button(fila, text="Abrir carpeta", command=self._abrir).pack(side="left", padx=8)
        self.estado = ttk.Label(fila, text="Listo.")
        self.estado.pack(side="left", padx=8)

        self.barra = ttk.Progressbar(m, mode="determinate", maximum=100)
        self.barra.pack(fill="x", pady=(6, 8))

        self.log = tk.Text(m, height=10, state="disabled", font=("Consolas", 9), bg="#111", fg="#ddd")
        self.log.pack(fill="both", expand=True)

        self.ffmpeg = buscar_ffmpeg()
        if not self.ffmpeg:
            self._log("⚠️  No encuentro ffmpeg: sin él no se pueden unir vídeo+audio ni sacar MP3.\n"
                      "    Instálalo con: winget install Gyan.FFmpeg")
        self.root.after(100, self._procesar_cola)

    # ── utilidades de interfaz ──────────────────────────────────────────
    def _pegar(self, _e):
        try:
            texto = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        self.urls.insert("insert", texto.strip() + "\n")
        return "break"

    def _elegir(self):
        d = filedialog.askdirectory(initialdir=self.destino.get() or str(BASE))
        if d:
            self.destino.set(d)

    def _abrir(self):
        d = Path(self.destino.get())
        d.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(d)
        else:
            subprocess.Popen(["xdg-open", str(d)])

    def _log(self, texto):
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _procesar_cola(self):
        try:
            while True:
                tipo, valor = self.cola.get_nowait()
                if tipo == "log":
                    self._log(valor)
                elif tipo == "progreso":
                    self.barra["value"] = valor
                elif tipo == "estado":
                    self.estado.configure(text=valor)
                elif tipo == "fin":
                    self.trabajando = False
                    self.boton.configure(state="normal")
                    self.barra["value"] = 100 if valor else self.barra["value"]
        except queue.Empty:
            pass
        self.root.after(100, self._procesar_cola)

    # ── descarga ────────────────────────────────────────────────────────
    def empezar(self):
        if self.trabajando:
            return
        urls = [u.strip() for u in self.urls.get("1.0", "end").splitlines() if u.strip()]
        urls = [u for u in urls if re.match(r"https?://", u)]
        if not urls:
            messagebox.showwarning("Descargador YT", "Pega al menos una URL (https://...).")
            return
        try:
            desde, hasta = a_segundos(self.desde.get()), a_segundos(self.hasta.get())
        except ValueError as e:
            messagebox.showerror("Descargador YT", str(e))
            return
        if desde is not None and hasta is not None and hasta <= desde:
            messagebox.showerror("Descargador YT", "'Hasta' tiene que ser mayor que 'desde'.")
            return
        destino = Path(self.destino.get().strip() or CARPETA_DESCARGAS)
        destino.mkdir(parents=True, exist_ok=True)
        self.trabajando = True
        self.boton.configure(state="disabled")
        self.barra["value"] = 0
        threading.Thread(target=self._descargar,
                         args=(urls, FORMATOS[self.formato.get()], destino, desde, hasta),
                         daemon=True).start()

    def _descargar(self, urls, fmt, destino, desde, hasta):
        try:
            import yt_dlp
        except ImportError:
            self.cola.put(("log", "❌ Falta yt-dlp. Ejecuta INSTALAR.bat"))
            self.cola.put(("fin", False))
            return

        ok_total = True
        for i, url in enumerate(urls, 1):
            pref = f"[{i}/{len(urls)}] " if len(urls) > 1 else ""
            self.cola.put(("estado", f"{pref}Preparando…"))
            self.cola.put(("progreso", 0))

            def gancho(d, pref=pref):
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    hecho = d.get("downloaded_bytes") or 0
                    if total:
                        self.cola.put(("progreso", hecho * 100 / total))
                    vel = d.get("speed") or 0
                    self.cola.put(("estado", f"{pref}Descargando… {hecho / 1e6:.1f} MB"
                                             f"{f' de {total / 1e6:.1f} MB' if total else ''}"
                                             f"{f' · {vel / 1e6:.1f} MB/s' if vel else ''}"))
                elif d["status"] == "finished":
                    self.cola.put(("estado", f"{pref}Procesando…"))

            opts = {
                "outtmpl": str(destino / "%(title).80B [%(id)s].%(ext)s"),
                "noplaylist": True,
                "windowsfilenames": True,
                "progress_hooks": [gancho],
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "retries": 5,
                "fragment_retries": 5,
            }
            opts.update({k: v for k, v in fmt.items()})
            if self.ffmpeg:
                opts["ffmpeg_location"] = self.ffmpeg
            if desde is not None or hasta is not None:
                from yt_dlp.utils import download_range_func
                opts["download_ranges"] = download_range_func(None, [(desde or 0, hasta if hasta is not None else float("inf"))])
                opts["force_keyframes_at_cuts"] = True
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    titulo = info.get("title", url) if info else url
                self.cola.put(("log", f"✅ {titulo}"))
            except Exception as e:
                ok_total = False
                msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e))
                self.cola.put(("log", f"❌ {url}\n   {msg}"))
                if "Sign in" in msg or "confirm" in msg:
                    self.cola.put(("log", "   (YouTube pide iniciar sesión para este vídeo; prueba con otro)"))
                elif "Requested format" in msg or "nsig" in msg or "JavaScript" in msg:
                    self.cola.put(("log", "   Suele arreglarse actualizando: ejecuta INSTALAR.bat otra vez."))

        self.cola.put(("estado", "Terminado ✔" if ok_total else "Terminado con errores"))
        self.cola.put(("fin", ok_total))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
