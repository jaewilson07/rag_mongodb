"""Google Drive collector implementing the SourceCollector protocol."""

from __future__ import annotations

from typing import List

from mdrag.ingestion.models import (
    CollectedSource,
    GoogleDriveCollectionRequest,
    SourceContent,
    SourceContentKind,
    ingestion_timestamp,
)
from mdrag.ingestion.protocols import SourceCollector
from mdrag.integrations.google_drive import (
    AsyncGoogleDriveClient,
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_PDF_EXPORT,
    GOOGLE_SLIDES_MIME_TYPE,
)
from mdrag.integrations.models import SourceFrontmatter
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.settings import Settings, load_settings

logger = get_logger(__name__)


class GoogleDriveCollector(SourceCollector[GoogleDriveCollectionRequest]):
    """Collect Google Drive content for ingestion."""

    name = "gdrive"

    def __init__(
        self,
        drive_client: AsyncGoogleDriveClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.drive_client = drive_client

    async def collect(
        self, request: GoogleDriveCollectionRequest
    ) -> List[CollectedSource]:
        """Collect Drive sources and normalize for ingestion."""
        if not self.settings.google_service_account_file:
            await logger.warning(
                "collector_gdrive_missing_credentials",
                action="collector_gdrive_missing_credentials",
            )
            return []

        await logger.info(
            "collector_gdrive_start",
            action="collector_gdrive_start",
            file_ids=len(request.file_ids),
            folder_ids=len(request.folder_ids),
            doc_ids=len(request.doc_ids),
        )

        client = self._get_drive_client()
        file_ids = list(request.file_ids) + list(request.doc_ids)

        for folder_id in request.folder_ids:
            try:
                files = await client.list_files_in_folder(folder_id)
                file_ids.extend([file.get("id") for file in files if file.get("id")])
            except Exception as exc:
                await logger.error(
                    "collector_gdrive_folder_failed",
                    action="collector_gdrive_folder_failed",
                    folder_id=folder_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        collected: List[CollectedSource] = []
        seen: set[str] = set()
        for file_id in file_ids:
            if not file_id or file_id in seen:
                continue
            seen.add(file_id)
            try:
                metadata = await client.get_file(file_id)
                name = metadata.get("name", file_id)
                mime_type = metadata.get("mimeType", "")

                if mime_type in {GOOGLE_DOC_MIME_TYPE, GOOGLE_SLIDES_MIME_TYPE}:
                    file_bytes = await client.export_file(
                        file_id,
                        GOOGLE_PDF_EXPORT,
                    )
                    filename = f"{name}.pdf"
                else:
                    file_bytes = await client.download_file(file_id)
                    filename = name

                source_url = metadata.get("webViewLink") or (
                    f"https://drive.google.com/file/d/{file_id}/view"
                )

                frontmatter = SourceFrontmatter(
                    source_type="gdrive",
                    source_url=source_url,
                    source_title=name,
                    source_id=file_id,
                    source_mime_type=mime_type,
                    source_web_view_url=metadata.get("webViewLink"),
                    source_created_at=metadata.get("createdTime"),
                    source_modified_at=metadata.get("modifiedTime"),
                    source_etag=metadata.get("etag"),
                    source_description=metadata.get("description"),
                    source_owners=[
                        owner.get("displayName", owner.get("emailAddress", "Unknown"))
                        for owner in metadata.get("owners", [])
                    ],
                    source_fetched_at=ingestion_timestamp(),
                )

                collected.append(
                    CollectedSource(
                        frontmatter=frontmatter,
                        content=SourceContent(
                            kind=SourceContentKind.BYTES,
                            data=file_bytes,
                            filename=filename,
                            mime_type=mime_type,
                        ),
                        metadata={"gdrive": metadata},
                        namespace=request.namespace,
                    )
                )
            except Exception as exc:
                await logger.error(
                    "collector_gdrive_file_failed",
                    action="collector_gdrive_file_failed",
                    file_id=file_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        await logger.info(
            "collector_gdrive_complete",
            action="collector_gdrive_complete",
            collected_count=len(collected),
        )
        return collected

    def _get_drive_client(self) -> AsyncGoogleDriveClient:
        if not self.drive_client:
            self.drive_client = AsyncGoogleDriveClient(
                self.settings.google_service_account_file,
                subject=self.settings.google_impersonate_subject,
            )
        return self.drive_client


__all__ = ["GoogleDriveCollector"]
