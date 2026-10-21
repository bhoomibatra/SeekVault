from seekvault.embeddings.text_embedder import TextEmbedder
from seekvault.embeddings.image_embedder import ImageEmbedder

class EmbeddingManager:
    _text_embedder = None
    _image_embedder = None

    @classmethod
    def get_text_embedder(cls) -> TextEmbedder:
        if cls._text_embedder is None:
            cls._text_embedder = TextEmbedder()
        return cls._text_embedder

    @classmethod
    def get_image_embedder(cls) -> ImageEmbedder:
        if cls._image_embedder is None:
            cls._image_embedder = ImageEmbedder()
        return cls._image_embedder
