# dpgs-analysis-2026: how actively are digital public goods developed?

Notebooks, data and code behind the blog post *[title and link to the post: to be added]* by Greg Maly.

The study looks at the **digital public goods (DPGs)** listed by the DPG Alliance and at their public GitHub activity from
January 2020 to 29 October 2026. It asks:

1. Are DPG teams building AI features into their products?
2. How many people do sustained work on a DPG, and how much does each of them produce?
3. Who reviews changes before they are merged, and how often do pull requests say AI helped write them?
4. Did DPGs whose owners depended on US foreign aid lose contributors after the 2025 funding cuts?

## The notebooks

Read them in order. Each is commented step by step and saved with its output. Notebooks 01 to 05 read only the files in `data/`:
no account, no token and no internet connection are needed.

| notebook | what it shows | open in Colab |
|---|---|---|
| `00_how_the_data_came_in.ipynb` | How the data were collected: the ten pipeline steps from registry to finished files. Read mode needs nothing; demo mode runs one small DPG (GitHub token). | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamaly/dpgs-analysis-2026/blob/main/00_how_the_data_came_in.ipynb) |
| `01_registry_and_sample.ipynb` | The registry, the confidence tiers and how 256 listed DPGs become the 166 DPGs / 190 repositories used everywhere. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamaly/dpgs-analysis-2026/blob/main/01_registry_and_sample.ipynb) |
| `02_teams_and_activity.ipynb` | Core contributors per DPG, output per core contributor, ageing, features, newcomers and the slice by Sustainable Development Goal. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamaly/dpgs-analysis-2026/blob/main/02_teams_and_activity.ipynb) |
| `03_ai_features.ipynb` | Are teams building AI features into their products, and do those reach a release? | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamaly/dpgs-analysis-2026/blob/main/03_ai_features.ipynb) |
| `04_review_and_ai_disclosure.ipynb` | Who reviews merged pull requests, and how much AI-assisted coding is disclosed. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamaly/dpgs-analysis-2026/blob/main/04_review_and_ai_disclosure.ipynb) |
| `05_funding_exposure_and_cuts.ipynb` | US aid exposure, terminated awards and what happened to the teams after the 2025 cuts. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamaly/dpgs-analysis-2026/blob/main/05_funding_exposure_and_cuts.ipynb) |

Every number used in the post is computed in a cell headed `### Claim N...` (N001, N002 and so on). The post's footnotes cite these
ids: search a notebook for the id to find the cell. Each of notebooks 01 to 05 ends with a plain printed summary of the numbers it computed.

## Run it

**In Google Colab:** click a badge above. The first code cell copies this repository into the Colab session; nothing has to be installed.

**On your computer:**
```
git clone https://github.com/gamaly/dpgs-analysis-2026.git
cd dpgs-analysis-2026
pip install -r requirements.txt
jupyter lab        # start it in this folder, then open the notebooks
```

Notebook 00 starts in `read` mode, which fetches and writes nothing. Its `demo` mode re-runs the real collection for one small DPG and
needs a GitHub token (a `GITHUB_TOKEN` environment variable or a `.env` file; in Colab it asks for it with a hidden prompt).

## What is in the folders

| path | content |
|---|---|
| `data/` | only the datasets that notebooks 01 to 05 read (column descriptions in `extras/DATA_DICTIONARY.md`) |
| `extras/pipeline/` | the scripts that collected and processed the data. They need the raw GitHub download (1.9 GB, not published) and a token, so they are here to show exactly what was done rather than to be re-run |
| `extras/DATA_DICTIONARY.md` | what every column of every file in `data/` means; the Form 990 codebook is a section at the end |

## Data sources

* The DPG Alliance registry (`app.digitalpublicgoods.net/api/dpgs`), read on 29 October 2026.
* GitHub's public GraphQL and REST APIs: pull requests, issues, releases, tags and commits for the matched repositories.
* Public funding records: US federal award data (USAspending.gov), IRS Form 990 data (ProPublica Nonprofit Explorer and IRS files), the list of terminated US aid awards, and IATI donor data.

Everything is public data. Individuals are not identified: person ids are hashed, and no names, logins, e-mail addresses or pull request text are published.

## Read this before quoting the numbers

* "Core contributors" are people active in at least 2 of the 3 months of a quarter. This is a proxy for sustained work, not a head count of paid staff.
* AI figures are rough counts: telling readers that AI helped is voluntary, and a rise partly reflects more telling.
* "Exposed to US aid" describes the organisation that owns a DPG, not its code team. Only 8 of the 12 exposed DPGs can be measured on GitHub. The results show association, not causation.
* Only DPGs listed today are studied, GitHub shows code work only, and work moved to private repositories looks like a drop.

## Licences

* Code (notebooks and `extras/pipeline/`): MIT, see `LICENSE`.
* Data (`data/` and `extras/DATA_DICTIONARY.md`): CC BY 4.0, see `LICENSE-DATA`. The underlying public sources keep their own terms.

## How to cite

Maly, G. (2026). *Digital public goods activity data and code, 2020-2026* [data set and code]. https://github.com/gamaly/dpgs-analysis-2026. Accompanies the post [link to be added].

## Contact

[contact details: to be added]
