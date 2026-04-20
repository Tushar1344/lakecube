#!/usr/bin/env bash
#
# Pull a real Sample.Basic outline + data from a running docker-essbase
# container and feed them through the Lakecube importer.
#
# Prereqs (see docs/testing-with-docker-essbase.md):
#   - docker-essbase built and started (`docker-compose up --build --detach`)
#   - the `essbase` container healthy (takes ~30 min on first build)
#   - Sample.Basic loaded (automatic on first boot)
#
# Usage:
#   # from the lakecube repo root:
#   ./scripts/essbase/parity.sh [path/to/docker-essbase]
#
# If the docker-essbase path isn't passed, the script assumes
# ../_oracle_sandbox/docker-essbase (the layout this repo prepares).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ESSBASE_DIR="${1:-$REPO_ROOT/../_oracle_sandbox/docker-essbase}"
CONTAINER="${ESSBASE_CONTAINER:-essbase}"

STARTDIR="$ESSBASE_DIR/start_scripts"
OUTDIR_HOST="$STARTDIR/output"
OUTDIR_CONTAINER="/home/oracle/start_scripts/output"
FIXTURES_DIR="$REPO_ROOT/tests/fixtures/oracle"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# --- Preflight ---------------------------------------------------------------

step "Preflight"

command -v docker >/dev/null 2>&1 || fail "docker not on PATH — see docs/testing-with-docker-essbase.md"

[ -d "$ESSBASE_DIR" ] || fail "docker-essbase directory not found: $ESSBASE_DIR"
[ -d "$STARTDIR" ] || mkdir -p "$STARTDIR"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    fail "container '$CONTAINER' is not running. Start it with:
    cd $ESSBASE_DIR && docker-compose up --build --detach
Then wait for the Essbase service to become healthy (can take 30+ minutes on first build)."
fi

# --- Stage MaxL scripts into the bind-mounted volume -----------------------

step "Staging MaxL scripts into $STARTDIR"
cp "$REPO_ROOT/scripts/essbase/export-outline.msh" "$STARTDIR/"
cp "$REPO_ROOT/scripts/essbase/export-data.msh"    "$STARTDIR/"
mkdir -p "$OUTDIR_HOST"

# --- Run exports inside the container --------------------------------------

step "Exporting outline (attribute-rich + tree-mode)"
docker exec "$CONTAINER" bash -lc \
    "startMaxl.sh /home/oracle/start_scripts/export-outline.msh"

step "Exporting cell data (level-0 + all-cells)"
docker exec "$CONTAINER" bash -lc \
    "startMaxl.sh /home/oracle/start_scripts/export-data.msh"

# --- Collect outputs --------------------------------------------------------

mkdir -p "$FIXTURES_DIR"
step "Copying exports to $FIXTURES_DIR"
cp -v "$OUTDIR_HOST"/sample-basic-* "$FIXTURES_DIR/"

# --- Import the outline through Lakecube -----------------------------------

step "Running lakecube import outline against the real Oracle export"
PYTHON="${PYTHON:-python3}"
cd "$REPO_ROOT"

"$PYTHON" -m lakecube.cli.main import outline \
    "$FIXTURES_DIR/sample-basic-outline.xml" \
    --out "$FIXTURES_DIR/sample-basic.generated.cube.yaml" \
    --name "sample_basic_from_oracle"

"$PYTHON" -m lakecube.cli.main import outline \
    "$FIXTURES_DIR/sample-basic-outline.treemode.xml" \
    --out "$FIXTURES_DIR/sample-basic.treemode.generated.cube.yaml" \
    --name "sample_basic_from_oracle_tree"

step "Compile both generated cubes (sanity round-trip)"
"$PYTHON" -m lakecube.cli.main compile \
    "$FIXTURES_DIR/sample-basic.generated.cube.yaml" \
    --out "$REPO_ROOT/build/parity"
"$PYTHON" -m lakecube.cli.main compile \
    "$FIXTURES_DIR/sample-basic.treemode.generated.cube.yaml" \
    --out "$REPO_ROOT/build/parity"

step "Done"
echo "Artifacts:"
echo "  Real outline XML    : $FIXTURES_DIR/sample-basic-outline.xml"
echo "  Tree-mode outline   : $FIXTURES_DIR/sample-basic-outline.treemode.xml"
echo "  Level-0 data        : $FIXTURES_DIR/sample-basic-data.txt"
echo "  All-cells data      : $FIXTURES_DIR/sample-basic-data.allcells.txt"
echo "  Generated cube.yaml : $FIXTURES_DIR/sample-basic.generated.cube.yaml"
echo "  Compiled artifacts  : $REPO_ROOT/build/parity/"
echo
echo "Review differences against the handwritten fixtures at:"
echo "  $REPO_ROOT/tests/fixtures/Sample.Basic.xml"
echo "  $REPO_ROOT/tests/fixtures/Sample.Basic.treemode.xml"
