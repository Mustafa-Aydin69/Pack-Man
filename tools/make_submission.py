"""LMS teslim paketini üretir: README.txt + Pacman.exe + Kaynak Kodlar/.

Kullanım (proje klasöründe, EXE derlendikten sonra):

    python tools/make_submission.py dist/Pacman.exe Pacman.zip

Kaynak kod olarak git'in izlediği dosyalar alınır (derleme çıktıları, sanal
ortamlar ve önbellekler zaten git dışındadır). README.txt Windows Not
Defteri'nde doğru görünsün diye CRLF satır sonu ve UTF-8 BOM ile yazılır.
"""

import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_FOLDER = "Kaynak Kodlar"
# Teslim paketine girmeyen, yalnızca depo için olan dosyalar.
EXCLUDED_PREFIXES = (".github/", "submission/", ".gitignore", ".gitattributes")


def source_files():
    output = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [path for path in output.splitlines() if path and not path.startswith(EXCLUDED_PREFIXES)]


def build(exe_path, zip_path):
    with open(os.path.join(ROOT, "submission", "README.txt"), encoding="utf-8") as handle:
        readme = handle.read().replace("\r\n", "\n").replace("\n", "\r\n")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", "\ufeff" + readme)
        archive.write(exe_path, "Pacman.exe")
        files = source_files()
        for path in files:
            archive.write(os.path.join(ROOT, path), f"{SOURCE_FOLDER}/{path}")
    return len(files)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    count = build(*argv)
    print(f"{argv[1]}: README.txt, Pacman.exe ve {count} kaynak dosya")
    return 0


if __name__ == "__main__":
    sys.exit(main())
