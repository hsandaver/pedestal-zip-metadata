"""Bounded, read-only source inventory. No archive member is extracted."""
import base64
from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shlex
import stat
import zipfile

MODEL_EXTENSIONS = {'.obj', '.stl', '.ply', '.glb', '.gltf', '.fbx', '.dae', '.3ds', '.usd', '.usdz', '.usdc', '.usda'}

@dataclass(frozen=True)
class Limits:
    members: int = 10000
    total_bytes: int = 2 * 1024**3
    member_bytes: int = 512 * 1024**2
    metadata_bytes: int = 2 * 1024**2
    compression_ratio: int = 200
    line_bytes: int = 1024**2
    source_bytes: int = 1024**3


def safe_name(name):
    return bool(name) and not (name.startswith('/') or '\\' in name or '\x00' in name or re.match(r'^[A-Za-z]:', name) or '..' in PurePosixPath(name).parts)


def process(inputs, limits=None):
    from pedestal import parse_metadata
    limits = limits or Limits()
    result = {key: [] for key in ('catalogue', 'variants', 'manifest', 'issues')}
    seen_records = {}
    for number, source in enumerate(inputs, 1):
        name = str(source[0]) if isinstance(source, tuple) else str(source)
        sid = f's{number:04d}-' + hashlib.sha256(name.encode()).hexdigest()[:10]
        def issue(code, member, detail):
            result['issues'].append(dict(source_id=sid, source_name=name, member=member, code=code, detail=str(detail)))
        archive = None
        try:
            rows = []
            if not isinstance(source, tuple) and Path(source).is_dir():
                root = Path(source)
                if root.is_symlink():
                    issue('unsafe_member', '', 'Symlink input folder refused')
                    continue
                for directory, dirs, files in os.walk(root, followlinks=False):
                    for d in list(dirs):
                        p = Path(directory) / d
                        if p.is_symlink():
                            issue('unsafe_member', p.relative_to(root).as_posix(), 'Symlink directory refused')
                            dirs.remove(d)
                    for filename in sorted(files):
                        p = Path(directory) / filename
                        info = p.lstat()
                        rows.append((p.relative_to(root).as_posix(), p, info.st_size, not stat.S_ISREG(info.st_mode), 0))
                        if len(rows) > limits.members:
                            raise ValueError('Member count exceeds limit')
                def opener(entry):
                    # O_NOFOLLOW closes the final-component symlink race.
                    return os.fdopen(os.open(entry, os.O_RDONLY | os.O_NOFOLLOW), 'rb')
            else:
                source_size = len(source[1]) if isinstance(source, tuple) else Path(source).stat().st_size
                if source_size > limits.source_bytes:
                    raise ValueError('Compressed input size exceeds limit')
                archive = zipfile.ZipFile(io.BytesIO(source[1]) if isinstance(source, tuple) else source)
                infos = archive.infolist()
                if len(infos) > limits.members:
                    raise ValueError('Member count exceeds limit')
                for entry in infos:
                    mode = entry.external_attr >> 16
                    if not entry.is_dir():
                        rows.append((entry.filename, entry, entry.file_size, stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG}), entry.compress_size))
                opener = archive.open
            duplicates = Counter(posixpath.normpath(r[0]) for r in rows)
            entries = {}
            total = sum(r[2] for r in rows)
            for key, entry, size, unsafe, compressed in rows:
                status = 'accepted'
                if unsafe or not safe_name(key):
                    status = 'unsafe_member'
                elif duplicates[posixpath.normpath(key)] > 1:
                    status = 'duplicate_member'
                elif size > limits.member_bytes or total > limits.total_bytes:
                    status = 'size_limit'
                elif archive and size / max(compressed, 1) > limits.compression_ratio:
                    status = 'compression_limit'
                result['manifest'].append(dict(source_id=sid, source_name=name, member=key, size_bytes=size, status=status))
                if status != 'accepted':
                    issue(status, key, 'Member excluded from parsing; retained in manifest')
                else:
                    entries[posixpath.normpath(key)] = (entry, size)
            def decode(data, key):
                try:
                    return data.decode('utf-8'), 'utf-8'
                except UnicodeDecodeError:
                    issue('encoding_fallback', key, 'Decoded as Latin-1; original bytes preserved for metadata')
                    return data.decode('latin-1'), 'latin-1'
            def metadata(key):
                entry, size = entries[key]
                if size > limits.metadata_bytes:
                    issue('size_limit', key, 'Metadata exceeds text limit')
                    return None
                with opener(entry) as stream:
                    data = stream.read(limits.metadata_bytes + 1)
                if len(data) > limits.metadata_bytes:
                    issue('size_limit', key, 'Metadata exceeds text limit')
                    return None
                raw, encoding = decode(data, key)
                return raw, encoding, base64.b64encode(data).decode('ascii')
            def dependency_lines(key):
                entry, size = entries[key]
                if PurePosixPath(key).suffix.lower() == '.mtl' and size > limits.metadata_bytes:
                    raise ValueError(f'Material text exceeds metadata size limit: {key}')
                with opener(entry) as stream:
                    consumed = 0
                    while True:
                        data = stream.readline(limits.line_bytes + 1)
                        if not data:
                            break
                        consumed += len(data)
                        if consumed > limits.member_bytes or len(data) > limits.line_bytes:
                            raise ValueError(f'Dependency scan limit exceeded: {key}')
                        # Geometry need not be decoded or retained.
                        if data.lstrip().startswith((b'mtllib ', b'mtllib\t', b'map_', b'bump ', b'disp ', b'decal ', b'norm ')):
                            yield decode(data, key)[0].strip()
            objects = []
            for key in entries:
                if PurePosixPath(key).suffix.lower() != '.txt':
                    continue
                try:
                    item = metadata(key)
                    if item is None:
                        continue
                    raw, encoding, original = item
                    clean = raw.lstrip('\ufeff')
                    if re.search(r'^Title:', clean, re.M) and re.search(r'^(License:|Description:|Source:)', clean, re.M):
                        row = parse_metadata(raw)
                        row.update(source_id=sid, source_name=name, metadata_path=key, object_id=f'{sid}-o{len(objects)+1:04d}', metadata_encoding=encoding, raw_metadata_base64=original)
                        identity = row['source'] or row['catalogue_id'] or hashlib.sha256(raw.encode()).hexdigest()
                        if identity in seen_records:
                            issue('duplicate_record', key, f"Possible duplicate of {seen_records[identity]}; both retained")
                        seen_records[identity] = row['object_id']
                        objects.append(row)
                        result['catalogue'].append(row)
                    else:
                        issue('unrecognized_metadata', key, 'Text does not have Title plus License, Source or Description')
                except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
                    issue('member_error', key, exc)
            if not objects:
                issue('no_metadata', '', 'No recognized metadata documents')
            for key in entries:
                extension = PurePosixPath(key).suffix.lower()
                if extension not in MODEL_EXTENSIONS:
                    continue
                # Choose metadata at nearest ancestor, not a sibling object's document.
                candidates = []
                parent = PurePosixPath(key).parent
                for directory in (parent, *parent.parents):
                    candidates = [o for o in objects if PurePosixPath(o['metadata_path']).parent == directory]
                    if candidates:
                        break
                oid = candidates[0]['object_id'] if len(candidates) == 1 else ''
                if not oid:
                    issue('ambiguous_object', key, 'Cannot assign model to exactly one metadata document')
                match = re.search(r'(?:^|[_ .-])(high|medium|low)(?:v\d+)?(?=[_ .-]|$)', PurePosixPath(key).stem, re.I)
                variant = dict(source_id=sid, source_name=name, object_id=oid, model_path=key, model_format=extension[1:], filename_quality_label=match.group(1).lower() if match else '', quality_basis='filename label only' if match else '', material_files=[], textures=[], missing_dependencies=[], dependency_status='not_checked')
                result['variants'].append(variant)
                if extension != '.obj':
                    continue
                def resolve(base, reference):
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(base), reference))
                    if not safe_name(target) or target not in entries:
                        variant['missing_dependencies'].append(target)
                        issue('missing_dependency', key, target)
                    return target
                try:
                    for line in dependency_lines(key):
                        command, _, rest = line.replace('\t', ' ').partition(' ')
                        if command != 'mtllib':
                            continue
                        refs = shlex.split(rest, comments=True)
                        # An existing unquoted filename with spaces is unambiguous.
                        if posixpath.normpath(posixpath.join(posixpath.dirname(key), rest.strip())) in entries:
                            refs = [rest.strip()]
                        for ref in refs:
                            mtl = resolve(key, ref)
                            variant['material_files'].append(mtl)
                            if mtl not in entries:
                                continue
                            for ml in dependency_lines(mtl):
                                cmd, _, value = ml.replace('\t', ' ').partition(' ')
                                if cmd.startswith('map_') or cmd in {'bump', 'disp', 'decal', 'norm'}:
                                    if value.strip().startswith('-'):
                                        issue('unsupported_mtl_options', mtl, ml)
                                        variant['dependency_status'] = 'scan_incomplete'
                                        continue
                                    refs = shlex.split(value, comments=True)
                                    tex = resolve(mtl, ' '.join(refs))
                                    variant['textures'].append(tex)
                    if variant['dependency_status'] != 'scan_incomplete':
                        variant['dependency_status'] = 'missing' if variant['missing_dependencies'] else 'complete'
                    if not variant['material_files']:
                        issue('no_material_reference', key, 'OBJ has no mtllib declaration; no external material dependencies found')
                except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
                    variant['dependency_status'] = 'scan_incomplete'
                    issue('member_error', key, exc)
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
            issue('source_error', '', exc)
        finally:
            if archive:
                archive.close()
    return result
