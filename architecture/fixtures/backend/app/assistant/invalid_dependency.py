from app.documents.repository import DocumentRepository


def invalid_dependency() -> type[DocumentRepository]:
    return DocumentRepository
