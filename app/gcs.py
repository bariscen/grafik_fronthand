from google.cloud import storage
from google.cloud import storage
from google.oauth2 import service_account
import streamlit as st

BLOB_NAME = "cizim/aktif_cizim.pdf"

def upload_pdf_to_gcs(file_obj, bucket_name: str) -> str:
    # Streamlit Cloud -> credentials secrets'tan
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = storage.Client(
        credentials=creds,
        project=st.secrets["gcp_service_account"]["project_id"]
    )

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(BLOB_NAME)

    # Dosya başa sar
    try:
        file_obj.seek(0)
    except Exception:
        pass

    # Upload
    blob.upload_from_file(
        file_obj,
        content_type="application/pdf",
    )

    # Doğrula (bu satır kritik debug)
    blob.reload()
    if not blob.exists():
        raise RuntimeError("Upload sonrası blob bulunamadı (exists=False).")

    return f"gs://{bucket_name}/{BLOB_NAME}"

