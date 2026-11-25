import os
from pathlib import Path
from typing import Dict, Any, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DEFECTIQ"
    version: str = "2.0.0"
    # PostgreSQL is the application default.  SQLite remains an explicit local
    # development choice via DATABASE_URL=sqlite:///./defectiq.db.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/defectiq"
    qdrant_path: str = str(Path(__file__).resolve().parents[1] / "storage" / "qdrant")
    qdrant_url: str = ""
    collection_name: str = "eclipse_jdt_defects"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_local_files_only: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    dataset_path: str = "C:/Users/avina/Downloads/JDT/JDT_dataset_issues (1).csv"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: str = str(Path(__file__).resolve().parents[1] / "storage" / "uploads")
    max_upload_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_dataset(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate configured dataset path and return metadata."""
        if not self.dataset_path:
            return False, "DATASET_PATH environment variable is not configured.", {}
        
        path = Path(self.dataset_path)
        try:
            if not path.exists():
                return False, f"Configured dataset file does not exist at: {self.dataset_path}", {}
            
            if not path.is_file():
                return False, f"Configured dataset path is a directory, not a file: {self.dataset_path}", {}
            
            size_bytes = path.stat().st_size
            size_gb = round(size_bytes / (1024 ** 3), 2)
            size_mb = round(size_bytes / (1024 ** 2), 2)
            readable = os.access(path, os.R_OK)
            if not readable:
                return False, "Dataset file exists but is not readable by the current process.", {"path": str(path), "filename": path.name, "is_readable": False}
            return True, "Dataset file validated successfully.", {
                "path": str(path),
                "filename": path.name,
                "size_bytes": size_bytes,
                "size_gb": size_gb,
                "size_mb": size_mb,
                "is_readable": readable,
            }
        except PermissionError:
            return False, "Dataset exists but cannot be read due to a permission error.", {
                "path": str(path),
                "filename": path.name,
                "is_readable": False,
            }
        except Exception as exc:
            return False, f"Error inspecting dataset file: {exc}", {}

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return non-sensitive diagnostic snapshot for API consumers and Settings UI."""
        ds_valid, ds_msg, ds_meta = self.validate_dataset()
        db_type = "PostgreSQL" if "postgres" in self.database_url else "SQLite"
        
        return {
            "app_name": self.app_name,
            "version": self.version,
            "database_type": db_type,
            "database_connected": False,  # Updated dynamically by DB health check
            "qdrant_mode": "remote" if self.qdrant_url else "embedded_local",
            "qdrant_location": self.qdrant_url if self.qdrant_url else str(Path(self.qdrant_path).resolve()),
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "gemini_configured": bool(self.gemini_api_key and self.gemini_api_key.strip()),
            "gemini_model": self.gemini_model,
            "dataset_configured_path": self.dataset_path,
            "dataset_valid": ds_valid,
            "dataset_message": ds_msg,
            "dataset_metadata": ds_meta,
            "upload_dir": self.upload_dir,
        }


settings = Settings()
