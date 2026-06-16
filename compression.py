# compression.py
"""Utility functions for compressing a TinoProject into an archive.

This module provides a high-level :func:`compress_project` function that
collects the project's assets and creates a tarball using the appropriate
compression algorithm (gz, bz2, or lzma). Internal helpers ``_iter_assets``
and ``_compress_tar`` are deliberately kept private.

All functions use type hints and log their progress via the shared logger.
"""

import tarfile
from collections.abc import Iterable
from pathlib import Path
from config import TinoProject
from logger_config import get_logger

logger = get_logger()


def compress_project(project: TinoProject, output_path: str, extra_files: list[Path] | None = None) -> None:
    """Compress a :class:`~config.TinoProject` into an archive.

    Args:
        project: The project definition containing assets and compression settings.
        output_path: Destination file path for the created archive.
        extra_files: Optional additional files to include in the archive.
    """
    comp_type = project.compression_type
    level = project.compression_level

    logger.info(f"Gathering assets for compression (type: {comp_type}, level: {level})")
    assets = list(_iter_assets(project, extra_files))
    logger.info(f"Found {len(assets)} assets to compress")

    logger.info("Starting tar creation...")
    _compress_tar(assets, output_path, comp_type, level)
    logger.info("Tar creation finished.")


def _iter_assets(project: TinoProject, extra_files: list[Path] | None = None) -> Iterable[tuple[Path, str]]:
    """Yield ``(source_path, archive_name)`` tuples for all project assets.

    The generator walks the project's folders, files and any ``extra_files``
    supplied by the caller, ensuring that symlinks escaping the project root are
    ignored for safety.
    """
    folders = [p for d in set(project.folders) if (p := Path(d)).is_dir()]
    files = [p for f in set(project.files) if (p := Path(f)).is_file() or p.is_symlink()]

    for d_path in folders:
        parent = d_path.parent
        for item in d_path.rglob("*"):
            if item.is_file() or item.is_symlink():
                try:
                    resolved = item.resolve()
                    if not str(resolved).startswith(str(d_path.resolve())):
                        logger.warning(f"Skipping symlink escaping project directory: {item}")
                        continue
                except Exception:
                    logger.warning(f"Skipping unresolvable path: {item}")
                    continue
                arc = str(item.relative_to(parent))
                yield item, arc

    for f_path in files:
        arc = f_path.name
        yield f_path, arc

    if extra_files:
        for f_path in extra_files:
            yield f_path, f_path.name


def _compress_tar(assets: Iterable[tuple[Path, str]], output_path: str, comp_type: str, level: int) -> None:
    """Create a tar archive from *assets* using the requested compression.

    Args:
        assets: Iterable of ``(source_path, archive_name)`` tuples.
        output_path: Where to write the tar file.
        comp_type: Compression algorithm identifier (``gz``, ``bz2`` or ``lzma``).
        level: Compression level passed to the underlying ``tarfile`` module.
    """
    if comp_type == "lzma":
        tar = tarfile.open(output_path, mode="w:xz", preset=level)  # ty:ignore[no-matching-overload]
    elif comp_type == "bz2":
        tar = tarfile.open(output_path, mode="w:bz2", compresslevel=level)
    else:
        tar = tarfile.open(output_path, mode="w:gz", compresslevel=level)

    with tar:
        for src, arc in assets:
            logger.debug(f"Adding to archive: {src} -> {arc}")
            tar.add(src, arcname=arc, recursive=False)



