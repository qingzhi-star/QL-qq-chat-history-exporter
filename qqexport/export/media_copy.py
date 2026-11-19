"""只复制被引用媒体，按内容去重，独立副本不改源。"""
from __future__ import annotations

import hashlib
from tempfile import NamedTemporaryFile
from dataclasses import dataclass, field
from pathlib import Path

from qqexport.export.model import MediaRef
from qqexport.export.cancel import check_cancel


@dataclass
class CopyResult:
    copied: int = 0
    bytes_copied: int = 0
    missing: int = 0
    rel_by_source: dict[Path, str] = field(default_factory=dict)


def copy_media(refs: list[MediaRef], out_dir: Path, *, cancel=None) -> CopyResult:
    result = CopyResult()
    out_dir.mkdir(parents=True, exist_ok=True)
    for ref in refs:
        check_cancel(cancel)
        if ref.source is None or not ref.source.is_file():
            result.missing += 1
            continue
        if ref.source in result.rel_by_source:
            continue
        try:
            src = ref.source.open("rb")
        except FileNotFoundError:
            result.missing += 1
            continue
        digest = hashlib.sha256()
        size = 0
        temporary = None
        try:
            # 哈希和写入使用同一字节流。完整写出前不暴露最终文件名。
            with src, NamedTemporaryFile(dir=out_dir, prefix=".media-", delete=False) as dst:
                temporary = Path(dst.name)
                while block := src.read(1024 * 1024):
                    check_cancel(cancel)
                    dst.write(block)
                    digest.update(block)
                    size += len(block)
            check_cancel(cancel)
            name = digest.hexdigest() + ".bin"
            dest = out_dir / name
            if not dest.exists():
                temporary.replace(dest)
                result.copied += 1
                result.bytes_copied += size
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        result.rel_by_source[ref.source] = name
    return result
