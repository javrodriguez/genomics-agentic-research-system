"""Item-15 case surfaces, shared by construction and its regression controls."""
import io
from common import BASE_SHA, REPO, git

def base_blobs(source=REPO, revision=BASE_SHA):
    """Read exact base bytes at each path, without a filename allowlist."""
    import tarfile
    import build_cases
    result = {}
    with tarfile.open(fileobj=io.BytesIO(build_cases.base_archive(source, revision))) as archive:
        for member in archive.getmembers():
            if member.isfile():
                result[member.name] = archive.extractfile(member).read()
            elif member.issym():
                result[member.name] = member.linkname.encode('utf-8')
    return result


def decoded_objects(repo, revision):
    """Read reachable objects through Git, never compressed storage bytes."""
    ids = git(repo, 'rev-list', '--objects', '--no-object-names', revision).splitlines()
    stream = io.BytesIO(git(repo, 'cat-file', '--batch', input=b'\n'.join(ids) + b'\n'))
    objects = {}
    for oid in ids:
        actual, kind, size = stream.readline().split()
        assert actual == oid
        data = stream.read(int(size))
        assert stream.read(1) == b'\n'
        objects[oid] = (kind, data)
    return objects


def added_lines(patch):
    """Only plus lines inside hunks; headers and unchanged context are excluded."""
    in_hunk = False
    for line in patch.splitlines(keepends=True):
        if line.startswith(b'diff --git '):
            in_hunk = False
        elif line.startswith(b'@@ '):
            in_hunk = True
        elif in_hunk and line.startswith(b'+'):
            yield line[1:]


def added_case_surfaces(folder, manifest_bytes, patch, baseline):
    """Item 15: additions, decoded new objects, folder names and manifest.

    HEAD's parent has the base tree (checked independently by the builder test),
    without importing the original history. Q3's unchanged-line exemption also
    applies to decoded modified blobs; decoding must not reintroduce those lines.
    Q4 excludes storage bytes, never new commit metadata or new tree entries.
    The submitted patch is not a separate surface: read the committed diff.
    """
    repo = folder / 'repo'
    yield 'folder names', (folder.name + '/' + repo.name).encode('utf-8')
    yield 'manifest', manifest_bytes
    options = ('--no-ext-diff', '--no-textconv', '--no-color', '--no-renames', '--text', '-U0')
    diff = git(repo, 'diff', *options, 'HEAD~1', 'HEAD')
    yield 'added lines', b''.join(added_lines(diff))
    objects = decoded_objects(repo, 'HEAD')
    entries = git(repo, 'ls-tree', '-r', '-z', 'HEAD').split(b'\0')
    blobs = {}
    for entry in filter(None, entries):
        meta, name = entry.split(b'\t', 1)
        mode, kind, oid = meta.split()
        if kind != b'blob':
            continue
        relative = name.decode('utf-8')
        data = objects[oid][1]
        if relative not in baseline:
            # Even a copy of an inherited blob is a wholly added file (part i).
            yield 'added file ' + relative, data
            contribution = data
        elif baseline.get(relative) != data:
            contribution = b''.join(added_lines(git(
                repo, 'diff', *options, 'HEAD~1', 'HEAD', '--', relative)))
        else:
            contribution = b''
        blobs.setdefault(oid, []).append(contribution)
    inherited = decoded_objects(repo, 'HEAD~1^{tree}')
    inherited_content = {data for kind, data in inherited.values()}
    for oid, (kind, data) in objects.items():
        if oid in inherited or data in inherited_content:
            continue
        label = 'decoded ' + kind.decode('ascii') + ' ' + oid.decode('ascii')
        if kind == b'blob':
            # File additions are checked above even if the object is inherited.
            yield label, b''.join(blobs[oid])
        elif kind == b'tree':
            yield label, git(repo, 'cat-file', '-p', oid.decode('ascii'))
        else:
            yield label, data


def case_leaks(folder, manifest_bytes, patch, baseline, forbidden):
    return [(label, token) for label, data in
            added_case_surfaces(folder, manifest_bytes, patch, baseline)
            for token in forbidden if token.encode('utf-8') in data]
