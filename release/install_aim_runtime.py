"""Installe les bibliothèques officielles pour l'architecture locale."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
ASSETS = {
    'aarch64': ('linux_aarch64', '3bee10290ce7b46ec15bc1d48452d4e652ae91e478e8c7f2ba187fdc287a7f85'),
    'x86_64': ('linux_x64', '55648725838cae111c428131b619845b88fee45be61ea2d962e869ec0e8012aa'),
}
REQUIRED = {'vmm.so', 'leechcore.so', 'leechcore_ft601_driver_linux.so'}


def install():
    arch = platform.machine()
    if arch not in ASSETS:
        raise RuntimeError('Linux ARM64 ou x86-64 requis (OS 32 bits non pris en charge)')
    runtime = ROOT/'.runtime'
    runtime.mkdir(exist_ok=True)
    platform_name, expected = ASSETS[arch]
    filename = f'MemProcFS_files_and_binaries_v5.18.11-{platform_name}-20260914.tar.gz'
    url = 'https://github.com/ufrisk/MemProcFS/releases/download/v5.18/'+filename
    destination = runtime/'vmm'
    stamp = destination/'.asset-sha256'
    if (stamp.exists() and stamp.read_text().strip() == expected
            and all((destination/name).is_file() for name in REQUIRED)):
        print('Bibliothèques natives déjà installées.')
        return
    with tempfile.TemporaryDirectory(dir=runtime) as temp:
        temp = Path(temp)
        archive = temp/'runtime.tar.gz'
        digest = hashlib.sha256()
        print(f'Téléchargement des bibliothèques MemProcFS ({platform_name})…', flush=True)
        with urlopen(url, timeout=60) as response, archive.open('wb') as out:
            while chunk := response.read(1024*1024):
                out.write(chunk)
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError('Archive MemProcFS incorrecte (SHA-256), installation annulée')
        staged = temp/'vmm'
        staged.mkdir()
        with tarfile.open(archive) as tar:
            for member in tar:
                name = Path(member.name).name
                # Extraire uniquement les bibliothèques, données et licences, sans liens.
                if member.isfile() and (name.endswith('.so') or name == 'info.db' or 'license' in name.lower()):
                    with tar.extractfile(member) as src, (staged/name).open('wb') as out:
                        shutil.copyfileobj(src, out)
        if not all((staged/name).is_file() for name in REQUIRED):
            raise RuntimeError('Archive incomplète : bibliothèque DMA/FT601 absente')
        (staged/'.asset-sha256').write_text(expected+'\n')
        destination.mkdir(exist_ok=True)
        for source in staged.iterdir():
            os.replace(source, destination/source.name)
    print('Bibliothèques natives installées et vérifiées.')


if __name__ == '__main__':
    install()
