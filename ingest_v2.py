import concurrent.futures
import json
import os
import re
import urllib
import logging
from pathlib import Path

from typing import Union

import pandas as pd
from dotenv import load_dotenv

from tqdm import tqdm

import hashlib

load_dotenv()
EMAIL = os.environ["UNPAYWALL_EMAIL"]
UNPAYWALL_API_BASE = "https://api.unpaywall.org/v2"
URL_FORRT = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRgYcUP3ybhe4x05Xp4-GTf-Cn2snBCW8WOP_N7X-9r80AeCpFAGTfWn6ITtBk-haBkDqXAYXh9a_x4/pub?gid=1924034107&single=true&output=csv"


def load_url(url):
    with urllib.request.urlopen(url) as conn:
        return conn.read()


def import_data(url: str):
    return pd.read_csv(url)


def get_unpaywall_info(doi: str):
    url = f"{UNPAYWALL_API_BASE}/{doi}?email=michiel.van.der.ree@rug.nl"
    return load_url(url)


def download_and_save_pdf(pdf_url: str, doi: str, output_dir: Path):
    pdf_bytes = load_url(pdf_url)
    hash_filename = f"{hashlib.md5(doi.encode()).hexdigest()}.pdf"

    with output_dir.joinpath(hash_filename).open("wb") as f:
        f.write(pdf_bytes)

    return hash_filename


doi_pattern = re.compile(r"10\.\d{4,}/[\w/.-]+")


def get_doi_from_url(url: str):
    match = doi_pattern.search(url)
    return match.group() if match else None


def wrangle_data(df):
    """
    Standardize column names
    """
    df.columns = df.columns.str.lower()
    df.rename(
        columns={
            df.columns[df.columns.str.contains(pat="provider")][0]: "creators",
            df.columns[df.columns.str.contains(pat="url")][0]: "link_to_resource",
            df.columns[df.columns.str.contains(pat="material type")][
                0
            ]: "material_type",
            df.columns[df.columns.str.contains(pat="education level")][
                0
            ]: "education_level",
            df.columns[df.columns.str.contains(pat="conditions of use")][
                0
            ]: "conditions_of_use",
            df.columns[df.columns.str.contains(pat="primary user")][0]: "primary_user",
            df.columns[df.columns.str.contains(pat="subject areas")][
                0
            ]: "subject_areas",
            df.columns[df.columns.str.contains(pat="clusters")][0]: "FORRT_clusters",
            df.columns[df.columns.str.contains(pat="user tags")][0]: "tags",
        },
        inplace=True,
    )
    df.fillna("", inplace=True)
    return df


def split_cells(df):
    df["creators"] = [[y.strip() for y in x.split(",")] for x in df["creators"].values]
    df["primary_user"] = [
        [y.strip() for y in x.split(",")] for x in df["primary_user"].values
    ]
    df["material_type"] = [
        [y.strip() for y in x.split(",")] for x in df["material_type"].values
    ]
    df["education_level"] = [
        [y.strip() for y in x.split(",")] for x in df["education_level"].values
    ]
    df["subject_areas"] = [
        [y.strip() for y in x.split(",")] for x in df["subject_areas"].values
    ]
    df["FORRT_clusters"] = [
        [y.strip() for y in x.split(",")] for x in df["FORRT_clusters"].values
    ]
    df["tags"] = [[y.strip() for y in x.split(",")] for x in df["tags"].values]
    df["language"] = [[y.strip() for y in x.split(",")] for x in df["language"].values]
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = import_data(URL_FORRT)
    df = wrangle_data(df)

    df["doi"] = df["link_to_resource"].apply(get_doi_from_url)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {
            executor.submit(get_unpaywall_info, doi): idx
            for idx, doi in df["doi"].dropna().items()
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_idx),
            total=len(df["doi"].dropna()),
        ):
            idx = future_to_idx[future]
            try:
                data = future.result()
            except Exception as e:
                logging.error(f"Error processing DOI at index {idx}: {str(e)}")
                continue
            df.loc[idx, "unpaywall_info"] = data.decode("utf-8")

    df.to_json("data/interim/unpaywall_info.jsonl", lines=True, orient="records")

    df_info = pd.json_normalize(df["unpaywall_info"].dropna().apply(json.loads))

    pdf_dir = Path("data/pdfs")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {
            executor.submit(
                download_and_save_pdf,
                row["best_oa_location.url_for_pdf"],
                row.doi,
                pdf_dir,
            ): idx
            for idx, row in df_info.dropna(subset=["best_oa_location.url_for_pdf"]).iterrows()
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_idx),
            total=len(df_info.dropna(subset=["best_oa_location.url_for_pdf"])),
        ):
            idx = future_to_idx[future]
            try:
                pdf_path = future.result()
            except Exception as e:
                logging.error(f"Error processing DOI at index {idx}: {str(e)}")
                continue
            df_info.loc[idx, "pdf_path"] = pdf_path
