"""Private student submissions; local storage is development-only."""
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

MAX_FILE_BYTES = 4 * 1024 * 1024
EXTENSIONS = {'.pkt', '.pka', '.png', '.jpg', '.jpeg', '.pdf', '.txt', '.zip', '.pcap', '.pcapng'}
LOCAL_DIR = Path(os.getenv('UPLOAD_DIR', str(Path(__file__).parent / 'uploads')))


def cloud_enabled():
    return bool(os.getenv('BLOB_READ_WRITE_TOKEN') or os.getenv('BLOB_STORE_ID'))


async def save_file(upload):
    extension = Path(upload.filename or '').suffix.lower()
    if extension not in EXTENSIONS:
        raise HTTPException(400, 'Недопустимый формат файла')
    data = await upload.read(MAX_FILE_BYTES + 1)
    if not data:
        raise HTTPException(400, 'Файл пуст')
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, 'Максимум 4 МБ на файл')
    name = uuid.uuid4().hex + extension
    if cloud_enabled():
        from vercel import blob
        try:
            result = await blob.put_blob('submissions/' + name, data, access='private', content_type='application/octet-stream')
        except Exception as exc:
            raise HTTPException(503, 'Хранилище недоступно. Работа не отправлена; попробуйте позже.') from exc
        return 'blob:' + result.pathname
    if os.getenv('VERCEL'):
        raise HTTPException(503, 'Администратор ещё не подключил хранилище файлов')
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    (LOCAL_DIR / name).write_bytes(data)
    return name


async def file_response(reference):
    headers = {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'}
    if reference.startswith('blob:'):
        pathname = reference[5:]
        if not re.fullmatch(r'submissions/[a-f0-9]{32}\.[a-z0-9]+', pathname):
            raise HTTPException(404)
        from vercel import blob
        try:
            result = await blob.get_blob(pathname, access='private')
        except blob.BlobNotFoundError as exc:
            raise HTTPException(404, 'Файл не найден') from exc
        except Exception as exc:
            raise HTTPException(503, 'Хранилище временно недоступно') from exc
        headers['Content-Disposition'] = 'attachment; filename="submission' + Path(pathname).suffix + '"'
        return Response(result.body, media_type='application/octet-stream', headers=headers)
    if Path(reference).name != reference:
        raise HTTPException(404)
    path = LOCAL_DIR / reference
    if not path.is_file():
        raise HTTPException(404, 'Файл не найден')
    return FileResponse(path, filename='submission' + path.suffix, media_type='application/octet-stream', headers=headers)
