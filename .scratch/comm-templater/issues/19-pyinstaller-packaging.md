Status: resolved
Type: task
Blocked by: 11, 12, 13, 14, 15, 16, 17, 18

# 19 — PyInstaller Packaging

**What to build:** Package the complete application as a single executable. PyInstaller spec file configured for tkinter app. All dependencies bundled (pyserial, crc). Single .exe output that launches the full application on a clean Windows machine without Python installed.

**Blocked by:** All previous tickets (11–18).

**Status:** resolved — PyInstaller 6.22.2 / Python 3.14 ile build edildi

- [x] PyInstaller spec file configured for tkinter (`CommWorkbench.spec`, `build.bat`)
- [x] All dependencies bundled (`hiddenimports=['crc', 'serial']`)
- [x] Single .exe output — `dist/CommWorkbench.exe` (~10 MB, onefile, windowed)
- [x] Launches full application — exe `dist/configs/Test1`'i okudu, simülatöre TCP bağlandı, `comm.log`'u exe'nin yanına yazdı
- [ ] Temiz (Python'suz) makinede test edilmedi — bu makinede Python kurulu

**Notlar:**
- `config_loader.CONFIGS_DIR` artık `sys.frozen` ise `Path(sys.executable).parent / "configs"`; `main.py` ve `ui.py` bu tek kaynaktan alıyor
- exe'nin yanına `configs/` klasörü kopyalanmalı (`build.bat` bunu hatırlatıyor)
