#!/bin/bash
# G14 run 8 (15 Oct 2026; supersedes run7.sh, whose `umask 077` made the evidence folder 0700 and failed watcher-started): the no-model stub take (box/stub_take.py) over ssh on athena, from a git archive of the final
# merged head 383e5c2f, chained behind athena-gate.sh. No login, no model, no secret read.
# Usage: run7.sh <src.tar> <expected sha256 of src.tar>
set -euo pipefail
TAR=$1; WANT=$2
HERE=$(dirname "$0")
SSH=(ssh -a -x -o BatchMode=yes athena --)
[ "$(shasum -a 256 "$TAR" | cut -d' ' -f1)" = "$WANT" ] || { echo "tar sha256 mismatch"; exit 1; }
"$HERE/athena-gate.sh"
CHILD=$("${SSH[@]}" 'umask 077; mktemp -d /home/javier/w-XXXXXXXX')
echo "child: $CHILD"
scp -q -o BatchMode=yes -o ForwardAgent=no -o ForwardX11=no "$TAR" "athena:$CHILD/src.tar"
GOT=$("${SSH[@]}" "sha256sum $CHILD/src.tar | cut -d' ' -f1")
[ "$GOT" = "$WANT" ] || { echo "athena tar sha256 mismatch: $GOT"; exit 1; }
"$HERE/athena-gate.sh"
"${SSH[@]}" "set -e; mkdir -m 700 $CHILD/src $CHILD/scratch $CHILD/stub-take-20261015b; tar -xf $CHILD/src.tar -C $CHILD/src; \
 B=$CHILD/src/evals/gap-study-4/box; \
 nohup python3 -B \$B/stub_take.py --box \$B --scratch-parent $CHILD/scratch \
  --output $CHILD/stub-take-20261015b/stub-take.json \
  --gitleaks /home/javier/gap4-tools/gitleaks-8.30.1/gitleaks \
  --gitleaks-sha256 88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509 \
  --take-image sha256:336aa8cd024f0781c3ae3223e70bb0df15d9ad052fb1ec935deb2294b17c8b49 \
  --sidecar-image sha256:13d0597e231ca7f9176f77e8bc4b9f263bcdafd24e375f27145a7dc79e91069d \
  --egress-image sha256:5055a840860667f02f7425f855f27ac3ef3c6b16da19afb794863a66f8147674 \
  --codex-image sha256:21b214159e4eb02d5e73f78ccdf5ee047da2fc6944808f9a454a6b0f427dd381 \
  --gemini-image sha256:d10aa00b5958b00d1c719be1f0572967c04f30bfe381a427107c9e9a3f16b013 \
  --memory-reservation 2147483648 --cpus 8 --pids-limit 4096 \
  --seed-tree /home/javier/gap4-measure-20261014-boSnPQbA/admitted-20261014 \
  > $CHILD/run.out 2> $CHILD/run.err < /dev/null & echo pid=\$!"
