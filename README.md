# ESCAPIST — Exploring Star Clusters: Astrometric Parameter Intervals Selection Tool

*(formerly SCAPST, "Star Cluster Astrometric Parameters Selection Tool")*

**Live app: <https://scapst.streamlit.app/>** — open it in a browser, no installation needed.

A web application for finding the **optimal astrometric intervals** (proper motion and parallax) for separating an open star cluster from the Galactic field, using Gaia data. It runs in the browser and is built with [Streamlit](https://streamlit.io).

The method and the original desktop (Tkinter) program are described in:

> V. O. Mikhnevich, A. F. Seleznev. *Method for selecting stars from Gaia EDR3 for statistical investigation of an open cluster.* Ural Federal University, 2022.

![ESCAPIST: the start page with the NGC 6124 example](docs/images/app-overview.png)

*The start page: short guide, parameter inputs on the left, iteration table on the right.*

![Cluster star count versus iteration for NGC 6124](docs/images/plateau-plot.png)

*Cluster star count versus iteration for the NGC 6124 example. The shaded band marks the plateau (iterations 4–9).*

> **Note on the hosted version.** Apps on free Streamlit hosting go to sleep after a period of inactivity. If you see a "this app has gone to sleep" page, press the button to wake it up; it restarts in a few moments. The first Gaia query after that can take a few minutes.

---

## Why this tool exists

Stars of an open cluster share an origin, so their parallaxes and proper motions are tightly clustered. Selecting stars by astrometric intervals therefore removes most field stars, but the choice of interval matters:

- an interval that is **too wide** lets in field stars, and large-scale fluctuations of the field density distort the cluster counts;
- an interval that is **too narrow** loses real members because of astrometric measurement errors.

For each cluster there is a range of intervals where the statistically determined number of cluster stars is **maximal and roughly constant** (a *plateau*). ESCAPIST helps you find it: you narrow the intervals step by step, watch the colour–magnitude diagram, the sky map and the cluster star count, and the app records every step so the plateau becomes visible.

## Features

- Choose a cluster from the **Dias et al. (2021)** catalogue (VizieR `J/MNRAS/504/356`); its position, proper motion and parallax are filled in automatically. NGC 6124 is preloaded as a worked example.
- Choose the Gaia release: **DR3**, **EDR3** or **DR2**.
- Set proper-motion (μα, μδ) and parallax (ϖ) intervals, cluster radius, magnitude limit and maximum number of sources.
- Live statistics for the current selection:
  - most probable μα, μδ, ϖ (1-D kernel density estimate), with the corresponding tangential velocities and distance;
  - total number of stars in the area, number inside the cluster circle, number in a background ring of equal area, and the **background-adjusted number of cluster stars**.
- Diagrams: colour–magnitude diagram, sky map in Galactic coordinates (with the cluster circle and background ring), and μα, μδ, ϖ versus G.
- An **iteration table** and a **star count vs. iteration** plot for finding the plateau; the table can be sorted by interval width and exported as CSV.
- Data are downloaded once for the widest intervals and **re-filtered locally** while you narrow them; a new Gaia query is made only when you widen the selection.
- Automatic **fallback servers** if the ESA Gaia Archive is unavailable (ARI Heidelberg, then VizieR on the fastest reachable mirror).

## Quick start

### Use online

Open <https://scapst.streamlit.app/>, pick a cluster and press **Calculate** (see [How to use](#how-to-use)).

### Run locally

```bash
git clone https://github.com/<your-account>/<your-repo>.git
cd <your-repo>
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run SCAPST.py
```

The app opens at <http://localhost:8501>. An internet connection is required (Gaia and VizieR are queried live). The file `logoimg.png` must be in the same folder as `SCAPST.py`; the app reads it at start-up.

### Deploy on Streamlit Community Cloud

1. Push the repository to GitHub (include `SCAPST.py`, `logoimg.png`, `requirements.txt`).
2. On <https://share.streamlit.io> create a new app, pick the repository and set `SCAPST.py` as the main file.
3. After changing the code, use *Manage app → Reboot*. If a query failed, also clear Streamlit's cache (press `C` in the app → *Clear cache*), because a failed result is cached for the same inputs.

## How to use

1. **Pick a cluster** in the *Cluster* drop-down (type to search), or keep the NGC 6124 example.
2. **Start with wide intervals.** A good first guess is about ±3–5 mas/yr in proper motion and ±0.5–0.8 mas in parallax around the cluster values. Starting wide matters: widening later triggers a new Gaia query, narrowing does not.
3. Set **Radius, arcmin** (cluster radius), **Magnitude Limit**, **Max Number of Sources** and the **Gaia Release**.
4. Press **Calculate**. The first run downloads the data and may take a few minutes.
5. Read the results: modes of the distributions, star counts, and the diagrams.
6. **Narrow the intervals** a little (for example by the same step on every limit), press **Calculate** again, and repeat. Each press adds a row to the iteration table.
7. In the right panel, look at **Cluster Star Count vs. Iteration**. The intervals where the count stays maximal and roughly constant are the optimal ones. Use *Sort by Interval Width* if you did not narrow monotonically, *Save Table* to export the CSV, and *Clear Table* to start over.
8. **Reset** clears the cache and the session and returns to the NGC 6124 example.

### Worked example: NGC 6124

The preset reproduces the setup of the paper (centre l = 340.73°, b = +5.98°, radius 116′, G ≤ 18). Narrowing the intervals in 12 steps (μα from [−1.9, 1.5] to [−0.58, 0.18] mas/yr, μδ from [−3.8, −0.4] to [−2.48, −1.72] mas/yr, ϖ from [0.6, 2.6] to [1.55, 1.65] mas) gives a plateau for steps 4–9, i.e. deviations of about ±(0.86–1.34) mas/yr in proper motion and ±(0.37–0.73) mas in parallax from the most probable values. The right-hand table is preloaded with the paper's values for this cluster, and the plateau is shaded in the plot. Exact counts from a live query can differ slightly from the paper (different Gaia release, row limit).

## Inputs and outputs

| Input | Meaning |
|---|---|
| Cluster | Name from the Dias et al. (2021) catalogue, or the NGC 6124 example. Fixes the centre (l, b). |
| min/max μα, μδ, ϖ | Selection intervals (mas/yr, mas/yr, mas) |
| Radius, arcmin | Cluster radius. The downloaded area is a box of ±3 radii around the centre. |
| Magnitude Limit | Gaia G-band limit |
| Max Number of Sources | Upper limit on rows returned (25 000 … unlimited) |
| Gaia Release | DR3, EDR3 or DR2 |

| Output | Meaning |
|---|---|
| μα, μδ, ϖ (modes) | Most probable values from a 1-D kernel density estimate |
| Vα, Vδ, dist | Tangential velocities (4.74·μ/ϖ, km/s) and distance (1000/ϖ, pc) |
| Stars in the area / circle / ring | Counts after the interval selection |
| Cluster stars, background-adjusted | Circle count minus ring count |
| Iteration table and plot | One row per **Calculate**, used to find the plateau |

## Repository layout

```
SCAPST.py          # the whole application (Streamlit)
logoimg.png        # page icon, read at start-up
requirements.txt   # Python dependencies
README.md          # this file
docs/TECHNICAL.md  # architecture, algorithms, caching, limitations
docs/images/       # screenshots used in this README
```

## Documentation

- [Technical description](docs/TECHNICAL.md): architecture, data flow, algorithms, caching rules, known limitations.

## Known limitations (short list)

- The cluster centre comes from the catalogue; it is not re-estimated and cannot be edited in the interface.
- The colour–magnitude diagram shows apparent G magnitude against observed BP−RP (no distance or extinction correction).
- If the number of returned rows reaches *Max Number of Sources*, the sample is silently truncated.
- Choosing the plateau is done by eye; there is no automatic fit.

See [docs/TECHNICAL.md](docs/TECHNICAL.md#12-known-limitations-and-open-issues) for the full list.

## Data sources and acknowledgements

This work uses data from the European Space Agency (ESA) mission [Gaia](https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis Consortium (DPAC, <https://www.cosmos.esa.int/web/gaia/dpac/consortium>). It also uses the VizieR catalogue access tool, CDS, Strasbourg, France (DOI: 10.26093/cds/vizier), the Dias et al. (2021) cluster catalogue, and the [astropy](https://www.astropy.org) and [astroquery](https://astroquery.readthedocs.io) packages.

## Citation

If you use this tool, please cite the paper above. *(Add the DOI or journal reference here when available.)*

## Authors

V. O. Mikhnevich, A. F. Seleznev — Ural Federal University.

## License

*(Choose and add a license, for example MIT, Apache-2.0 or GPL-3.0, and place the text in a `LICENSE` file.)*
