import hashlib
import json
from pathlib import Path

import pandas as pd

from config.settings import CREDENTIALS_FILE, GDRIVE_FOLDER_ID
from ingest.drive import authenticate, upload_file
from ingest.helpers import (
    URL_FORRT,
    download_and_save_pdf,
    execute_concurrent_tasks,
    get_doi_from_url,
    get_unpaywall_info_by_doi,
    get_unpaywall_info_by_title,
    wrangle_data_forrt,
)

URL_JUST_OS_DB = "https://drive.google.com/uc?id=1eMiimpcwcnVJT6k4PQ9xfz3Udvsejo6V"

if __name__ == "__main__":
    df_forrt = pd.read_csv(URL_FORRT)
    df_forrt = wrangle_data_forrt(df_forrt)

    df_just_os = pd.read_csv(URL_JUST_OS_DB)

    # first try to get the doi from the link
    df_forrt["doi"] = (
        df_forrt["link_to_resource"].apply(get_doi_from_url).str.lower().str.strip()
    )

    def get_unpaywall_info_for_row(row):
        if pd.notnull(row.doi):
            upw_info = json.loads(get_unpaywall_info_by_doi(row.doi))
        else:
            results = json.loads(get_unpaywall_info_by_title(row.title))["results"]
            upw_info = results[0]["response"] if len(results) else None
        return upw_info

    unpaywall_info = execute_concurrent_tasks(
        df_forrt.iterrows(), get_unpaywall_info_for_row
    )

    for idx, result in unpaywall_info.items():
        if result:
            df_forrt.loc[idx, "doi"] = result["doi"]
            df_forrt.loc[idx, "is_oa"] = result["is_oa"]
            if result["best_oa_location"]:
                df_forrt.loc[idx, "pdf_url"] = result["best_oa_location"]["url_for_pdf"]

    df_forrt["is_oa"] = df_forrt["is_oa"].astype("boolean")

    df_forrt.loc[df_forrt["doi"].notna(), "doi_hash"] = df_forrt.loc[
        df_forrt["doi"].notna(), "doi"
    ].apply(lambda x: hashlib.md5(x.encode("utf-8")).hexdigest())

    pdf_dir = Path("data/pdfs")
    pdf_output_dir = pdf_dir / "by-doi"

    # try to download all pdfs that we don't have locally yet
    df_forrt.loc[df_forrt["doi"].notna(), "pdf_exists"] = df_forrt["doi_hash"].apply(
        lambda x: (pdf_output_dir / f"{x}.pdf").exists()
    )

    # for _, row in df_forrt.query("pdf_url.notna()").iterrows():
    #     download_and_save_pdf(row["pdf_url"], row["doi"], pdf_output_dir)

    _ = execute_concurrent_tasks(
        df_forrt.query("pdf_url.notna()").iterrows(),
        lambda row: download_and_save_pdf(row["pdf_url"], row["doi"], pdf_output_dir),
    )

    df_forrt["pdf_exists"] = df_forrt["doi_hash"].apply(
        lambda x: (pdf_output_dir / f"{x}.pdf").exists()
    )

    df_to_append = df_forrt.query("is_oa == True and pdf_exists == True")[
        df_just_os.columns
    ]

    pd.concat(
        [df_just_os, df_to_append.query("~doi_hash.isin(@df_just_os.doi_hash)")],
        ignore_index=True,
    ).to_csv("data/processed/just-os_db.csv", index=False)

    creds = authenticate(CREDENTIALS_FILE)
    upload_file(
        "data/processed/just-os_db.csv",
        GDRIVE_FOLDER_ID,
        creds,
        exists_ok=True,
        remote_filename="just-os_db_latest.csv",
    )
