from dataclasses import dataclass
from typing import List

@dataclass
class TextChunk:
    chunk_index: int
    page_number: int
    start_char_idx: int
    end_char_idx: int
    text: str

class TextChunker:
    """
    Sliding window passage chunker splitting extracted text into manageable passages
    for Sentence Transformer vector embedding.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, page_number: int = 1) -> List[TextChunk]:
        if not text or not text.strip():
            return []

        cleaned_text = text.strip()
        text_len = len(cleaned_text)

        if text_len <= self.chunk_size:
            return [
                TextChunk(
                    chunk_index=0,
                    page_number=page_number,
                    start_char_idx=0,
                    end_char_idx=text_len,
                    text=cleaned_text
                )
            ]

        chunks: List[TextChunk] = []
        step = self.chunk_size - self.overlap
        chunk_idx = 0

        for start in range(0, text_len, step):
            end = min(start + self.chunk_size, text_len)
            chunk_str = cleaned_text[start:end].strip()
            if chunk_str:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_idx,
                        page_number=page_number,
                        start_char_idx=start,
                        end_char_idx=end,
                        text=chunk_str
                    )
                )
                chunk_idx += 1

            if end >= text_len:
                break

        return chunks
