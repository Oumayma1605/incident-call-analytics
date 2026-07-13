"""
Anonymization pipeline for the incident & call datasets.

This script never leaves personal data in the output. It runs once, locally,
against the raw exports and produces two clean CSV files under data/processed/.
The raw files and the name -> code mapping table are NOT part of the GitHub
repository (see .gitignore).

Run:
    python src/anonymize.py
"""

import re
import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

INCIDENT_FILES = ["incident_-_2024-08.xlsx", "incident_-_2024-09.xlsx"]
CALL_FILES = ["new_call_08-2024.xlsx", "new_call_09-2024.xlsx"]

# Columns dropped outright: no analytical value, only re-identification risk
INCIDENT_DROP_COLS = [
    "Localisation", "Notes de travail", "Call ID", "Mis à jour par",
]
CALL_DROP_COLS = ["Description"]

PERSON_COLS_INCIDENT = ["Ouvert par", "Appelant", "Affecté à", "Résolu par"]
PERSON_COLS_CALL = ["Ouvert par"]


def build_person_codebook(frames, person_cols, prefix):
    """Assign a stable anonymous code to every distinct person name found."""
    names = set()
    for df, cols in zip(frames, person_cols):
        for c in cols:
            if c in df.columns:
                names |= set(df[c].dropna().astype(str).str.strip().unique())
    names -= {"", "nan", "NaN"}
    codebook = {name: f"{prefix}_{i+1:04d}" for i, name in enumerate(sorted(names))}
    return codebook


def anonymize_text_column(series, codebook):
    """Replace any known real name that leaks into free-text fields."""
    def scrub(text):
        if not isinstance(text, str):
            return text
        for name, code in codebook.items():
            if name and name in text:
                text = text.replace(name, code)
        return text
    return series.apply(scrub)


def load_incidents():
    frames = [pd.read_excel(RAW_DIR / f, sheet_name="Page 1") for f in INCIDENT_FILES]
    for f, df in zip(INCIDENT_FILES, frames):
        df["source_month"] = f
    return frames


def load_calls():
    frames = [pd.read_excel(RAW_DIR / f, sheet_name="Page 1") for f in CALL_FILES]
    for f, df in zip(CALL_FILES, frames):
        df["source_month"] = f
    return frames


def main():
    inc_frames = load_incidents()
    call_frames = load_calls()

    # one shared codebook per role so the same person gets the same code
    # across both the incident and call datasets
    agent_names = set()
    for df in inc_frames:
        for c in ["Ouvert par", "Affecté à", "Résolu par"]:
            agent_names |= set(df[c].dropna().astype(str).str.strip().unique())
    for df in call_frames:
        agent_names |= set(df["Ouvert par"].dropna().astype(str).str.strip().unique())
    agent_names -= {"", "nan", "NaN"}
    agent_codebook = {n: f"Agent_{i+1:03d}" for i, n in enumerate(sorted(agent_names))}

    caller_names = set()
    for df in inc_frames:
        caller_names |= set(df["Appelant"].dropna().astype(str).str.strip().unique())
    caller_names -= {"", "nan", "NaN"}
    caller_codebook = {n: f"Caller_{i+1:04d}" for i, n in enumerate(sorted(caller_names))}

    # ---- incidents ----
    incidents = pd.concat(inc_frames, ignore_index=True)
    incidents = incidents.drop(columns=[c for c in INCIDENT_DROP_COLS if c in incidents.columns])

    for col in ["Ouvert par", "Affecté à", "Résolu par"]:
        incidents[col] = incidents[col].astype(str).str.strip().map(agent_codebook).fillna(incidents[col])
    incidents["Appelant"] = incidents["Appelant"].astype(str).str.strip().map(caller_codebook).fillna(incidents["Appelant"])

    # belt-and-braces: scrub any leaked full name out of the short description
    full_codebook = {**agent_codebook, **caller_codebook}
    incidents["Description courte"] = anonymize_text_column(incidents["Description courte"], full_codebook)

    # ---- calls ----
    calls = pd.concat(call_frames, ignore_index=True)
    calls = calls.drop(columns=[c for c in CALL_DROP_COLS if c in calls.columns])
    calls["Ouvert par"] = calls["Ouvert par"].astype(str).str.strip().map(agent_codebook).fillna(calls["Ouvert par"])
    calls["Description brève"] = anonymize_text_column(calls["Description brève"], full_codebook)

    # rename to clean English snake_case headers for the analysis layer
    incidents = incidents.rename(columns={
        "Numéro": "ticket_id", "Type de contact": "contact_type", "Ouvert": "opened_at",
        "Ouvert par": "opened_by", "Groupe du créateur": "creator_group", "Appelant": "caller",
        "User Type": "user_type", "Template ID": "template_id", "Description courte": "short_description",
        "Société": "company", "Catégorie": "category", "Sous-catégorie": "subcategory",
        "Élément de configuration": "configuration_item", "Service": "service", "Environment": "environment",
        "État": "state", "État de l'incident": "incident_state", "Affecté à": "assigned_to",
        "Mise à jour": "updated_at", "Major incident state": "major_incident_state",
        "Incident parent": "parent_incident", "Incidents enfants": "child_incidents",
        "Résolu": "resolved_at", "Résolu par": "resolved_by", "Résolu par le groupe": "resolved_by_group",
        "Code de fermeture": "closure_code", "Nombre de réouvertures": "reopen_count",
        "Updated by End User": "updated_by_end_user", "Domaine": "domain",
        "Reassignment count Assignee": "reassignment_count", "Groupe d'affectation": "assignment_group",
        "First Call Resolution": "first_call_resolution", "Knowledge Article": "knowledge_article",
        "Article de connaissance": "knowledge_article_used",
    })

    calls = calls.rename(columns={
        "Numéro": "call_id", "Ouvert par": "opened_by", "Ouvert": "opened_at",
        "Call direction": "call_direction", "Call reason": "call_reason",
        "Type d'appel": "call_type", "Transféré à": "linked_incident",
        "Description brève": "short_description", "Société": "company",
    })

    incidents.to_csv(OUT_DIR / "incidents_clean.csv", index=False)
    calls.to_csv(OUT_DIR / "calls_clean.csv", index=False)

    print(f"incidents: {incidents.shape[0]} rows, {incidents.shape[1]} columns -> {OUT_DIR/'incidents_clean.csv'}")
    print(f"calls: {calls.shape[0]} rows, {calls.shape[1]} columns -> {OUT_DIR/'calls_clean.csv'}")
    print(f"agents anonymized: {len(agent_codebook)} | callers anonymized: {len(caller_codebook)}")


if __name__ == "__main__":
    main()
