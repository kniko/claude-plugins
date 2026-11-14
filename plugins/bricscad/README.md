# bricscad

**Ελληνικά** · [English](README.en.md)

Χειρισμός ενός ανοιχτού **BricsCAD** (Windows, V26, COM automation) από το Claude Code.

- **MCP server** `bricscad` (`server/server.py`, τρέχει με `uv`): κατάσταση, άνοιγμα και αποθήκευση σχεδίων,
  LISP και γραμμή εντολών, ερωτήματα για entities, solids, layers και extents, διαγραφή, zoom, screenshot,
  plot σε PDF, εξαγωγή DXF, και `export_geometry` (JSON· το `server/blender_import.py` το φέρνει στο Blender).
- **Skill** `bricscad`: πώς σχεδιάζονται κατόψεις, τομές και όψεις με ελληνικό κείμενο, μετρημένες διαστάσεις,
  διαγραμμίσεις σκυροδέματος και 3D solids. Python generators που γράφουν ASCII LISP (`scripts/cadlisp.py`),
  ανάγνωση των αποτελεσμάτων, και οι παγίδες (κόλλημα του PNGOUT, το παράθυρο «Save As» του PDF,
  χαμένες επιλογές).
- **Add-in ClaudeBridge** (`bridge/`, C# .NET 8, φορτώνεται στο BricsCAD με το εργαλείο `bridge_load`):
  named pipe (μόνο για τον τρέχοντα χρήστη των Windows) που δίνει στο MCP `lisp` με επιστροφή τιμής,
  την `selection` του χρήστη, `bridge_status`, `cancel`, και εντολές που απαντούν «busy» αντί να κολλάνε
  σε dialog ή prompt. Το `bridge/bin/ClaudeBridge.dll` είναι έτοιμο· για νέο build:
  `dotnet build -c Release -o ..\bin` στο `bridge/src` (.NET 8 SDK, BricsCAD V26· άλλος φάκελος: `BRICSCAD_DIR`).

## Απαιτήσεις

- Windows με ανοιχτό το BricsCAD (ή άφησε το `start_bricscad` να το ξεκινήσει).
- [`uv`](https://docs.astral.sh/uv/) στο PATH (`winget install astral-sh.uv`). Τις εξαρτήσεις του server
  (`mcp`, `pywin32`, `pillow`) τις εγκαθιστά το `uv` στο πρώτο τρέξιμο.

## Εγκατάσταση

```bash
claude plugin marketplace add kniko/claude-plugins
claude plugin install bricscad@kniko-tools
```

Αν είχες προσθέσει παλιότερα τον server με το χέρι (`claude mcp add bricscad ...`), αφαίρεσε εκείνη την
εγγραφή (`claude mcp remove bricscad -s user`), ώστε να μην τρέχει δύο φορές.
