#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
import yaml
from PIL import Image

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 320
GALLERY_CONFIG = Path('gallery.yml')
PHOTO_METADATA = Path('photos.yml')

# Future enhancement ideas:
# - `layout: inline` (current behavior) outputs one image block per item.
# - `layout: responsive` could emit multiple images on the same line and rely on GitHub to wrap.
# - `layout: table` could produce a fixed-column grid with captions in a second row.
# - `photos.yml` can be extended to include alt text, ordering, featured flags, and hide/show control.
# These are notes only; the current implementation remains inline-only.
GALLERY_START = '<!-- gallery:start -->'
GALLERY_END = '<!-- gallery:end -->'


def parse_args():
    parser = argparse.ArgumentParser(description='Generate thumbnails and update README gallery.')
    parser.add_argument('--images', required=True, help='Path to the source images directory.')
    parser.add_argument('--thumbnails', required=True, help='Path to the output thumbnails directory.')
    parser.add_argument('--readme', required=True, help='Path to the README file to update.')
    return parser.parse_args()


def get_images(source_dir: Path):
    return sorted(
        p for p in source_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and not p.name.startswith('.')
    )


def load_gallery_config():
    default = {'layout': 'inline'}
    if not GALLERY_CONFIG.exists():
        GALLERY_CONFIG.write_text('layout: inline\n', encoding='utf-8')
        return default

    with GALLERY_CONFIG.open('r', encoding='utf-8') as handle:
        config = yaml.safe_load(handle) or {}
    return {'layout': config.get('layout', 'inline')}


def load_photo_metadata(image_files):
    metadata = {}
    if PHOTO_METADATA.exists():
        with PHOTO_METADATA.open('r', encoding='utf-8') as handle:
            metadata = yaml.safe_load(handle) or {}

    updated = False
    for image_path in image_files:
        if image_path.name not in metadata:
            metadata[image_path.name] = {'caption': ''}
            updated = True
        elif metadata[image_path.name] is None:
            metadata[image_path.name] = {'caption': ''}
            updated = True

    if updated or not PHOTO_METADATA.exists():
        PHOTO_METADATA.write_text(yaml.safe_dump(metadata, sort_keys=True), encoding='utf-8')

    return metadata


def normalize_caption(filename: str):
    stem = Path(filename).stem
    caption = stem.replace('_', ' ').replace('-', ' ').replace('@', ' @ ')
    caption = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', caption)
    caption = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', caption)
    caption = ' '.join(caption.split())
    return caption


def generate_thumbnail(source_path: Path, thumb_path: Path):
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image.convert('RGB')
        image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.LANCZOS)
        image.save(thumb_path, quality=90, optimize=True)


def ensure_thumbnails(image_files, thumbnails_dir: Path):
    changed = False
    for image_path in image_files:
        thumb_path = thumbnails_dir / image_path.name
        if not thumb_path.exists() or image_path.stat().st_mtime > thumb_path.stat().st_mtime:
            print(f'Generating thumbnail: {thumb_path}')
            generate_thumbnail(image_path, thumb_path)
            changed = True
    return changed


def build_gallery_markdown(image_files, thumbnails_dir: Path, images_dir: Path, metadata, layout: str):
    if not image_files:
        return 'No images found in the gallery.\n'

    if layout == 'responsive':
        return build_responsive_gallery_markdown(image_files, thumbnails_dir, images_dir, metadata)

    # Current behavior: inline layout with one image block per item.
    # Future options could include:
    # - responsive inline wrapping: multiple images on one line, allowing viewport-based flow.
    # - fixed-column table: predictable columns with captions below each thumbnail.
    lines = ['## Image Gallery', '']
    for image_path in image_files:
        thumb_rel = thumbnails_dir.joinpath(image_path.name).as_posix()
        image_rel = images_dir.joinpath(image_path.name).as_posix()
        image_meta = metadata.get(image_path.name, {}) or {}
        caption = image_meta.get('caption') or normalize_caption(image_path.name)
        lines.append(f'[![{caption}]({thumb_rel})]({image_rel})  ')
        lines.append(caption)
        lines.append('')

    return '\n'.join(lines)


def build_responsive_gallery_markdown(image_files, thumbnails_dir: Path, images_dir: Path, metadata):
    lines = ['## Image Gallery', '']
    image_links = []
    for image_path in image_files:
        thumb_rel = thumbnails_dir.joinpath(image_path.name).as_posix()
        image_rel = images_dir.joinpath(image_path.name).as_posix()
        image_meta = metadata.get(image_path.name, {}) or {}
        caption = image_meta.get('caption') or normalize_caption(image_path.name)
        title = caption.replace('"', '\\"')
        image_links.append(f'[![{caption}]({thumb_rel} "{title}")]({image_rel})')

    lines.append('  '.join(image_links))
    lines.append('')
    return '\n'.join(lines)


def update_readme(readme_path: Path, gallery_md: str):
    content = readme_path.read_text(encoding='utf-8')
    if GALLERY_START in content and GALLERY_END in content:
        before, remainder = content.split(GALLERY_START, 1)
        _, after = remainder.split(GALLERY_END, 1)
        new_content = f'{before}{GALLERY_START}\n\n{gallery_md}\n{GALLERY_END}{after}'
    else:
        trimmed = content.rstrip() + '\n\n'
        new_content = f'{trimmed}{GALLERY_START}\n\n{gallery_md}\n{GALLERY_END}\n'
    readme_path.write_text(new_content, encoding='utf-8')


def main():
    args = parse_args()
    images_dir = Path(args.images)
    thumbnails_dir = Path(args.thumbnails)
    readme_path = Path(args.readme)

    if not images_dir.is_dir():
        raise SystemExit(f'Images directory not found: {images_dir}')
    if not readme_path.exists():
        raise SystemExit(f'README file not found: {readme_path}')

    config = load_gallery_config()
    layout = config['layout']
    if layout not in {'inline', 'responsive'}:
        raise SystemExit('Unsupported layout: {}. Supported layouts are inline and responsive.'.format(layout))

    image_files = get_images(images_dir)
    metadata = load_photo_metadata(image_files)
    ensure_thumbnails(image_files, thumbnails_dir)
    gallery_markdown = build_gallery_markdown(image_files, thumbnails_dir, images_dir, metadata, layout)
    update_readme(readme_path, gallery_markdown)


if __name__ == '__main__':
    main()
