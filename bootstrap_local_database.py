import hashlib
import json
from pathlib import Path
from ingest.drive import authenticate, upload_file

from config.settings import CREDENTIALS_FILE, GDRIVE_FOLDER_ID

import pandas as pd

from ingest.helpers import (
    execute_concurrent_tasks,
    get_doi_from_url,
    get_unpaywall_info_by_doi,
    get_unpaywall_info_by_title,
    wrangle_data_justos,
)

if __name__ == "__main__":
    df = pd.read_csv("data/raw/forrt_db_250627.csv")
    df = wrangle_data_justos(df)

    df["doi"] = df["link_to_resource"].apply(get_doi_from_url).str.lower().str.strip()

    pdf_dir = Path("data/pdfs")
    pdf_input_dir = pdf_dir / "by-justos-id"
    df["pdf_exists"] = df["just_os_id"].apply(
        lambda x: (pdf_input_dir / f"{x:04d}.pdf").exists()
    )

    has_pdf = df["pdf_exists"]

    def get_unpaywall_info_for_row(row):
        if pd.notnull(row.doi):
            upw_info = json.loads(get_unpaywall_info_by_doi(row.doi))
        else:
            results = json.loads(get_unpaywall_info_by_title(row.title))["results"]
            upw_info = results[0]["response"] if len(results) else None
        return upw_info

    unpaywall_info = execute_concurrent_tasks(
        df[has_pdf].iterrows(), get_unpaywall_info_for_row
    )

    for idx, result in unpaywall_info.items():
        if result:
            df.loc[idx, "doi"] = result["doi"]
            df.loc[idx, "is_oa"] = result["is_oa"]

    df["is_oa"] = df["is_oa"].astype("boolean")

    df.loc[df.is_oa, "doi_hash"] = df.loc[df.is_oa, "doi"].apply(
        lambda x: hashlib.md5(x.encode("utf-8")).hexdigest()
    )

    pdf_output_dir = pdf_dir / "by-doi"

    for _, row in df.query("is_oa == True").iterrows():
        just_os_id = row["just_os_id"]
        doi_hash = row["doi_hash"]

        # Format source filename with leading zeros (e.g., 0001.pdf)
        source_filename = f"{just_os_id:04d}.pdf"
        source_path = pdf_input_dir / source_filename

        # Create target filename with doi_hash
        target_filename = f"{doi_hash}.pdf"
        target_path = pdf_output_dir / target_filename

        target_path.write_bytes(source_path.read_bytes())

    df.query("is_oa == True").drop(
        ["just_os_id", "is_downloaded", "pdf_exists", "is_oa"], axis=1
    ).to_csv("data/processed/just-os_db.csv", index=False)

    creds = authenticate(CREDENTIALS_FILE)
    upload_file(
        "data/processed/just-os_db.csv",
        GDRIVE_FOLDER_ID,
        creds,
        exists_ok=True,
        remote_filename="just-os_db_init.csv",
    )
    upload_file(
        "data/processed/just-os_db.csv",
        GDRIVE_FOLDER_ID,
        creds,
        exists_ok=False,
        remote_filename="just-os_db_latest.csv",
    )
