"""Package the readable Firefox extension without a compiler or external dependencies."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text())
files = ['LICENSE', 'manifest.json', 'devtools.html', 'panel.html', 'popup.html']
files += [p.relative_to(root).as_posix() for folder in ['src', 'icons'] for p in (root / folder).rglob('*') if p.is_file()]
out = root.parent / ('devtools-unified-fixer-firefox-' + manifest['version'] + '.zip')
with ZipFile(out, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
    for name in sorted(files):
        archive.write(root / name, name)
with ZipFile(out) as archive:
    assert archive.testzip() is None
    for name in files:
        assert archive.read(name) == (root / name).read_bytes()
print(out)
