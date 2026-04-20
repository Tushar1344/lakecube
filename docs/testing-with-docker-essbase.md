# Testing the outline importer against a real Essbase instance

We can run Oracle Essbase 11.1.2.4 locally via [Applied OLAP's
docker-essbase](https://github.com/appliedolap/docker-essbase) (MIT-licensed)
and feed its real outline + data exports through the Lakecube importer. This
is the highest-fidelity test we can do without a production EPM environment.

Everything here is a **one-time setup**. Once the container is running,
`scripts/essbase/parity.sh` does the full export-and-import loop end-to-end.

## One-time prereqs

### 1. Install a Docker runtime

Either one works:

- **Docker Desktop** (Mac/Windows, GUI): <https://www.docker.com/products/docker-desktop/>.
  Needs admin password to install, accepts the license on first launch.
- **Colima** (headless, lighter on Apple Silicon):
  ```
  brew install colima docker docker-compose
  colima start --cpu 4 --memory 8 --disk 40
  ```

Either way, `docker ps` should work from a terminal before you continue.

### 2. Get the Oracle installer zipfiles

docker-essbase needs these six files in its root directory (not extracted):

| File | Size | Source |
|---|---|---|
| `Foundation-11124-linux64-Part1.zip` | ~1.2 GB | Oracle Software Delivery Cloud |
| `Foundation-11124-linux64-Part2.zip` | ~1.5 GB | Oracle Software Delivery Cloud |
| `Foundation-11124-linux64-Part4.zip` | ~1.0 GB | Oracle Software Delivery Cloud |
| `Foundation-11124-Part3.zip`         | ~1.5 GB | Oracle Software Delivery Cloud |
| `Essbase-11124-linux64.zip`          | ~1.4 GB | Oracle Software Delivery Cloud |
| `jdk-7u211-linux-x64.tar.gz`         |  ~180 MB | Oracle Java archive |

How to get them:
1. Create a free Oracle account (if you don't have one).
2. Go to <https://edelivery.oracle.com/> → search *Oracle Hyperion Foundation Services 11.1.2.4*.
3. Accept the license, filter by "Linux x86-64", download the five EPM zips.
4. Separately: the JDK comes from the [Oracle Java SE Archive](https://www.oracle.com/java/technologies/javase/javase7-archive-downloads.html) — grab 7u211 for Linux x64.

Total download: ~6.6 GB.

### 3. Clone docker-essbase and drop the files in

This repo already placed a clone at `../_oracle_sandbox/docker-essbase/`
(sibling of the `lakecube/` repo). Drop the six files there:

```bash
cd /Users/tushar.madan/work_agent/_oracle_sandbox/docker-essbase
ls *.zip *.tar.gz   # should list all six
```

### 4. Build and start the container

```bash
cd /Users/tushar.madan/work_agent/_oracle_sandbox/docker-essbase
docker-compose up --build --detach
./follow-essbase-logs.sh   # tail the startup logs
```

First build can take **20–40 minutes** (Oracle installer runs inside the
container). Essbase is ready when the logs show:

```
Esbase Server initialized successfully.
Waiting for Essbase applications to start...
```

On Apple Silicon Macs, expect emulation overhead — the container runs
`linux/amd64` under Rosetta 2 / qemu. Functional but slower.

Once up, you can sanity-check via the bundled MaxL shell:

```bash
cd ../docker-essbase
./essbash.sh
# now inside the container:
startMaxl.sh
MAXL> login 'admin' "$EPM_PASSWORD" on localhost;
MAXL> display database;   /* should list sample.basic, demo.basic, ASOsamp.sample */
MAXL> logout;
MAXL> exit;
```

## One-button parity test

Once the container is healthy and Sample.Basic is loaded (auto-loaded on first
boot via `load-sample-databases.msh`):

```bash
cd /Users/tushar.madan/work_agent/lakecube
./scripts/essbase/parity.sh
```

This will:

1. Copy `scripts/essbase/export-outline.msh` and `export-data.msh` into the
   container's bind-mounted `start_scripts/` directory.
2. Run both via `startMaxl.sh`, producing:
   - `sample-basic-outline.xml` — attribute-rich outline (default mode)
   - `sample-basic-outline.treemode.xml` — sparse tree mode
   - `sample-basic-data.txt` — level-0 (leaf) cells
   - `sample-basic-data.allcells.txt` — all cells including rollups
3. Copy those into `tests/fixtures/oracle/`.
4. Run `lakecube import outline` against both XMLs, producing two generated
   `cube.yaml` files.
5. Compile both through the full emitter pipeline as a round-trip sanity check.

After a successful run, eyeball the diff:

```bash
diff tests/fixtures/Sample.Basic.xml tests/fixtures/oracle/sample-basic-outline.xml
diff tests/fixtures/Sample.Basic.treemode.xml tests/fixtures/oracle/sample-basic-outline.treemode.xml
```

Gaps between the handwritten and real fixtures are the next hardening pass
for the importer.

## Credentials reference

From `docker-essbase/.env`:

| Variable | Value |
|---|---|
| `EPM_ADMIN` | `admin` |
| `EPM_PASSWORD` | `password1` |
| `SQL_USER` (repo DB) | `sa` |
| `SQL_PASSWORD` (repo DB) | `AAbb11##` |

Essbase service port (exposed on host): **1423**.
Workspace UI: **http://localhost:9000/workspace/**.
EAS console: **http://localhost:9000/easconsole/**.

## Troubleshooting

- **Container won't start / hangs during install**: first build times out
  occasionally on Apple Silicon. `docker-compose logs essbase` surfaces the
  underlying error. Often a retry of `docker-compose up --build` works.
- **`startMaxl.sh: command not found`**: the container's login shell
  doesn't source Essbase env by default. `bash -lc 'startMaxl.sh ...'` (what
  `parity.sh` uses) picks up the right env. If running interactively, check
  that `/home/oracle/.bashrc` sources `setupEssbase.sh` or similar.
- **`Cannot find database sample.basic`**: Sample apps are loaded
  asynchronously on first boot. Wait for logs to show
  `Loaded: Sample.Basic data`. If never loaded, run
  `startMaxl.sh /home/oracle/start_scripts/load-sample-databases.msh`
  manually.
- **Exported XML is empty or tiny**: the `tree` option strips member
  attributes. `parity.sh` runs both modes to exercise both code paths.
