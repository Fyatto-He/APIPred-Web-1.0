# APIPred Web 1.0

Aptamer–Protein Interaction Prediction Tools. A web application that
generates and ranks candidate DNA aptamers for a target amino-acid
sequence using an XGBoost interaction model and ViennaRNA folding with
DNA thermodynamic parameters.

## Repository layout

```
backend/               FastAPI service (Python)
  main.py              Endpoints + prediction workflow
  utils/               Config, constraints, sequence utils, schemas
  models/              XGBoost model + feature extractor
  database/            SQLite schema + sequence-generation scripts
  tests/               Determinism check + committed golden results
frontend/              Next.js 15 app (TypeScript / Tailwind)
  app/                 Routes: /, /predict, /faq, /instructions,
                       /members, /license, /contact, /results/[jobId]
  app/components/      Shared components (Header, Footer, cards, viz scripts)
  app/content/         Editable data files (site metadata, nav, FAQ,
                       instructions, members, modules)
  public/              Static assets served at /
ViennaRNA-master/      Bundled ViennaRNA 2.7 (see Third-party software)
apipred.nginx.conf     Reverse proxy config for deployment
CHANGELOG.md           Notable changes
```

## Running locally

### Backend
```bash
cd backend
python -m venv env && source env/bin/activate
pip install -r requirements.txt
```

Then apply the **repDNA compatibility patch** described below — the
backend will not import without it — and start the server *from the
`backend/` directory*:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

`backend/` must be the working directory: the model paths in
`models/predictor.py` and `RESULTS_DB_PATH` in `utils/config.py` are
relative to it. (The DNA parameter file is resolved against `__file__`,
so that one works from anywhere.)

### repDNA compatibility patch (required)

`repDNA` on PyPI is a Python 2 package. Its modules import each other
with implicit relative imports, so on Python 3 the backend dies at
startup with:

```
ModuleNotFoundError: No module named 'nacutil'
```

Nine import lines across six files need a leading `.`. After
`pip install`, run:

```bash
python - <<'EOF'
import re, pathlib, site
sp = pathlib.Path(site.getsitepackages()[0]) / "repDNA"
mods = "nacutil|util|psenacutil|nac|ac|acutil|psenac"
for p in sp.glob("*.py"):
    s = p.read_text()
    t = re.sub(rf'^from ({mods}) import', r'from .\1 import', s, flags=re.M)
    if s != t:
        p.write_text(t)
        print("patched", p.name)
EOF
```

This is a site-packages change, not a repository one, so it must be
repeated whenever the virtualenv is recreated. It only rewrites import
statements — repDNA's numerics are untouched, and it normalizes k-mer
counts with an explicit `float()`, so the feature vectors are identical
under Python 2 and 3.

### Frontend
```bash
cd frontend
npm install
PORT=3000 npm run dev    # http://localhost:3000
```

`PORT` matters: `package.json` defaults to port 80, which needs root.
Port 3000 is also what the CORS allowlist in `main.py` and
`apipred.nginx.conf` expect.

For local development the frontend also needs to be told where the API
is. In production the two share an origin and nginx proxies `/api/`, so
the default `API_BASE` of `/api` resolves; there is no such proxy in
`next dev`. Create `frontend/.env.local` (untracked):

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### ViennaRNA
The backend imports the `RNA` Python module from ViennaRNA. The
`viennarna` entry in `requirements.txt` provides it — version 2.7.x
matches the source bundled at `ViennaRNA-master/`, and prebuilt wheels
exist for current Pythons, so no compilation is normally needed. To
build from the bundled source instead, follow the platform steps in
that project's `INSTALL` file. The bundled copy is included because a
few local patches were applied for compatibility with older Python
versions, and because `misc/dna_mathews2004.par` is loaded from it at
runtime.

Note that `requirements.txt` also lists `RNA`. That is an unrelated
PyPI package and is **not** the ViennaRNA binding; installing it can
shadow the real `RNA` module.

## Checking prediction determinism

The same query is expected to produce the same predictions in the same
order. `backend/tests/check_determinism.py` pins that behaviour to
golden files and fails if it changes:

```bash
cd backend
python tests/check_determinism.py                # ~2s
python tests/check_determinism.py --case full    # the UI's defaults, ~2.5 min
python tests/check_determinism.py --twice        # also require stability within one process
```

Run the fast case after any backend change and the full case before a
release. If a change is *meant* to alter predictions, regenerate the
goldens with `--update` and review the resulting diff deliberately —
that diff is the record of what the change did to the science.

Ordering is the fragile part. Most of a typical top 25 shares one
probability value, so ranks are decided by insertion order into
`BoundedResultsQueue` while eight threads fold concurrently; the
reordering step in `parallel_rna_folding_global` is what keeps it
stable. The check compares the ordered list for that reason.

## License

Released under **Creative Commons Attribution-NonCommercial-ShareAlike
4.0** (CC BY-NC-SA 4.0). See [LICENSE](LICENSE) for the summary and
`/license` in the running app for the full explanation.

## Citation

If you use APIPred Web 1.0 in your research, please cite:

- Fang Z, Wu Z, Wu X, Chen S, Wang X, Umrao S, Dwivedy A. *APIPred: An
  XGBoost-Based Method for Predicting Aptamer-Protein Interactions.*
  J Chem Inf Model. 2024 Apr 8;64(7):2290-2301.
  doi: 10.1021/acs.jcim.3c00713.
- Zhang C, He J, Gandavadi D, Hoang C.N.M., Cho H, Son M, Wang X,
  Dwivedy A, Umrao S. bioRxiv 2025.12.31.697194;
  doi: https://doi.org/10.64898/2025.12.31.697194

## Third-party software

This repository bundles **ViennaRNA 2.7** (in `ViennaRNA-master/`) under
its own license (see `ViennaRNA-master/ViennaRNA-master/license.txt`).
Proper credit belongs to the ViennaRNA authors and the **Institute for
Theoretical Chemistry, University of Vienna**.
Upstream project: https://www.tbi.univie.ac.at/RNA/

If your work uses the RNA / DNA folding produced by APIPred Web,
please additionally cite:

- Lorenz R, Bernhart S.H., Höner zu Siederdissen C, Tafer H,
  Flamm C, Stadler P.F., Hofacker I.L. *ViennaRNA Package 2.0.*
  Algorithms for Molecular Biology, 6:26 (2011).
- Hofacker I.L. *Fast folding and comparison of RNA secondary
  structures.* Monatshefte für Chemie 125(2):167-188 (1994).
