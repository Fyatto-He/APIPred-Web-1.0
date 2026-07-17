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
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev              # http://localhost:3000
```

### ViennaRNA
The backend imports the `RNA` Python module from ViennaRNA. Build it
once (from the bundled source at `ViennaRNA-master/`) with the
platform-appropriate steps from that project's `INSTALL` file, or
install the `viennarna` package via conda / your package manager. The
bundled copy is included because a few local patches were applied for
compatibility with older Python versions.

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
