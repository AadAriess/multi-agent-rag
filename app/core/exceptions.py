"""
Definisi exception kustom untuk aplikasi
"""


class BaseOriensSpaceException(Exception):
    """Kelas dasar untuk exception OriensSpace"""
    pass


class LLMException(BaseOriensSpaceException):
    """Exception untuk error terkait LLM"""
    pass


class DatabaseException(BaseOriensSpaceException):
    """Exception untuk error terkait database"""
    pass


class DocumentProcessingException(BaseOriensSpaceException):
    """Exception untuk error terkait pemrosesan dokumen"""
    pass