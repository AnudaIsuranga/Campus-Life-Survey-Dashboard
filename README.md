# Campus Life & Student Satisfaction Analytics Dashboard

A Dash + Plotly survey dashboard built from the uploaded coursework brief, Google Forms questionnaire, and collected 107-row dataset. The UI follows the supplied dark Figma screenshots while all calculated metrics are recomputed from the active dataset.

## Coursework alignment

- Survey-based project pool: questionnaire + data collection + analysis.
- 107 responses in the supplied dataset satisfy the minimum 100-response requirement.
- Pandas is used for ingestion, cleaning, validation, filtering, reshaping and summaries.
- Plotly charts are embedded in Dash and update from the filtered dataset.
- Interactive widgets: age group, gender, programme, visit frequency, buttons, upload and response search.
- Drill-down correlation uses Spearman rank correlation with a p-value.
- Professional multi-section dashboard with cards, plots, navigation, upload modal, response explorer and feedback view.
- Survey live-update requirement is handled as a batch-refresh workflow: uploaded datasets become the active dataset, the Refresh Data control re-renders the active analysis, and the console automatically refreshes its active view state on a 30-second interval.

## Files

```text
survey_dashboard/
├── app.py
├── requirements.txt
├── Procfile
├── README.md
├── assets/
│   └── style.css
├── data/
│   └── survey_responses.xlsx
└── utils/
    ├── __init__.py
    ├── analysis.py
    ├── charts.py
    └── data_processing.py
```

## Windows 11 + VS Code

Open PowerShell in this folder:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:8050
```

The app intentionally starts in an empty state. Use **Upload CSV/XLSX** and select the supplied `data\survey_responses.xlsx` file to activate the live analysis.

## Google Forms schema used by the app

The uploaded questionnaire contains:

- Q1 Age Group
- Q2 Gender
- Q3 Department/Programme
- Q4 Campus Visit Frequency
- Q5–Q17 satisfaction questions on the 1–5 Likert scale
- Q18 multi-select improvement areas
- Q19 personal mobile-data/hotspot frequency
- Q20 multi-select mobile-data reasons
- Q21 optional written feedback

The loader maps columns by question number so Google Forms header spacing differences do not break ingestion. The original uploaded column labels are not overwritten on disk; they are mapped into internal analysis fields only.

## Important dataset note

The Figma screenshots are used for **visual design**, not as a source of statistical truth. The supplied Excel file is used for the numbers. For example, the dashboard will calculate the improvement-area counts and satisfaction distributions from the uploaded 107-row dataset rather than copying values shown in the screenshots.

## Deployment

The included `Procfile` is ready for platforms such as Render using Gunicorn:

```text
web: gunicorn app:server
```

Set the platform's start command to the Procfile command if the platform does not detect it automatically.
