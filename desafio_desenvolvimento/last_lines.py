import os
import io
from codecs import BufferedIncrementalDecoder
from typing import Iterator

class ReverseUtf8Decoder(BufferedIncrementalDecoder):
    """
    A custom UTF-8 decoder that supports reverse reading of UTF-8 encoded files based on codecs.
    """
    def __init__(self, errors='strict'):
        super().__init__(errors)

    def decode(self, input: bytes, final: bool = False) -> str:
        """
        Decode input bytes (taking the buffer into account).

        Args:
            input (bytes): The chunk of bytes to decode.
            final (bool): If True, process the remaining buffer as the final input.

        Returns:
            str: Decoded UTF-8 string.
        """

        data = input + self.buffer
        result, consumed = self._buffer_decode(data, self.errors, final)
        self.buffer = data[:-consumed]  # Keep undecoded input until the next call

        return result

    def _buffer_decode(self, input: bytes, errors: str, final: bool) -> tuple[str, int]:
        """
        Decode the buffer, handling incomplete UTF-8 sequences.

        Args:
            input (bytes): Input buffer to decode.
            errors (str): Error handling scheme.
            final (bool): If True, process the remaining buffer as the final input.

        Returns:
            tuple[str, int]: Decoded string and number of bytes consumed.
        """
        result = []
        consumed = 0

        while input:
            try:
                # Attempt to decode the buffer from the end
                char, remaining = self._decode_last_character(input)
                result.append(char)
                consumed += len(input) - len(remaining)
                input = remaining
            except UnicodeDecodeError:
                break  # Stop if the buffer has an incomplete sequence

        if final and input:
            try:
                # Flush remaining data in the internal buffer
                char, _ = self._decode_last_character(input)
                result.append(char)
                consumed = len(input)
                input = b''
            except UnicodeDecodeError:
                raise ValueError("Incomplete UTF-8 character sequence at the end of input")

        return ''.join(reversed(result)), consumed

    def _decode_last_character(self, data: bytes) -> tuple[str, bytes]:
        """
        Decode the last UTF-8 character in a byte sequence.

        Args:
            data (bytes): Byte sequence to decode.

        Returns:
            tuple[str, bytes]: Decoded character and the remaining byte sequence.

        Raises:
            UnicodeDecodeError: If the byte sequence does not contain a valid UTF-8 character.
        """
        for i in range(1, 5):  # UTF-8 characters can be up to 4 bytes
            if len(data) < i:
                break
            try:
                # Try decoding the last i bytes
                char = data[-i:].decode('utf-8')
                return char, data[:-i]
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("utf-8", data, len(data) - i, len(data), "invalid continuation byte")

def is_utf8(file_path: str) -> bool:
    """Check if a file is encoded in UTF-8."""
    try:
        with open(file_path, 'rb') as f:
            f.read().decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False

def read_chunk(file, position: int, size: int) -> bytes:
    """Read a chunk of bytes from the file at the specified position."""
    file.seek(position)
    return file.read(size)

def process_buffer_utf8(buffer: bytes, decoder) -> Iterator[str]:
    """Decode and yield reversed UTF-8 chunks from the buffer."""
    decoded_chunk = decoder.decode(buffer, final=False)

    if decoded_chunk:
        yield decoded_chunk

def process_buffer_non_utf8(buffer: bytes) -> Iterator[str]:
    """Decode and yield reversed non-UTF-8 chunks from the buffer."""
    yield buffer.decode('latin1')  # Assuming non-UTF-8 content is latin1-encoded

def handle_final_chunk(buffer: bytes, utf8: bool, decoder) -> Iterator[str]:
    """Handle and yield the final chunk of data."""
    if utf8:
        try:
            final_chunk = decoder.decode(buffer, final=True)
            if final_chunk:
                yield final_chunk
        except UnicodeDecodeError:
            raise ValueError("The file contains incomplete UTF-8 characters at the end.")
    else:
        yield buffer.decode('latin1')

def last_lines(file_path: str, buffer_size: int = io.DEFAULT_BUFFER_SIZE) -> Iterator[str]:
    """
    Returns an iterator that reads the file in reverse, piece by piece.

    Args:
        file_path (str): Path to the file to read.
        buffer_size (int): Number of bytes to read at a time.

    Yields:
        str: A piece of the file content read in reverse.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    utf8 = is_utf8(file_path)

    # Open file with pointer positioned at the end, reading upwards
    with open(file_path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()

        remaining = file_size
        buffer = b''

        decoder = ReverseUtf8Decoder() if utf8 else None

        while remaining > buffer_size:
            chunk = read_chunk(f, remaining - buffer_size, buffer_size)
            buffer = chunk + buffer
            remaining -= buffer_size

            if utf8:
                yield from process_buffer_utf8(buffer, decoder)
            else:
                yield from process_buffer_non_utf8(buffer)
            buffer = b''

        # Process the final chunk
        f.seek(0)
        chunk = f.read(remaining)
        buffer = chunk + buffer

        yield from handle_final_chunk(buffer, utf8, decoder)

# Testing function
def run_tests():
    # Define test files
    files = {
        "utf8_file.txt": "This is a UTF-8 encoded file.\nIt contains multiple lines.\n最後の行はUTF-8でエンコードされています。\n".encode("utf-8"),
        "non_utf8_file.txt": "This is a non-UTF-8 file.\nIt will be encoded in Latin-1.\nLinha final em Latin-1.\n".encode("latin1"),
        "utf8_incomplete.txt": "This file will trigger an error.\nThe last line is cut off in UTF-8:\n最後の行は途中でカットされています。".encode("utf-8")[:-1]
    }

    # Create files
    for filename, content in files.items():
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
        with open(filename, mode, encoding=encoding) as f:
            f.write(content)

    test_cases = [
        ("utf8_file.txt", 3),  # UTF-8 file, small buffer size
        ("non_utf8_file.txt", 20),  # Non-UTF-8 file, larger buffer size
        ("utf8_incomplete.txt", None),  # UTF-8 file with incomplete character at the end - not recognized as utf-8
    ]

    for file, buffer_size in test_cases:
        print(f"Testing {file} with buffer size {buffer_size}...")
        try:
            if buffer_size:
                for line in last_lines(file, buffer_size):
                    print(line)
            else:
                for line in last_lines(file):
                    print(line)
        except ValueError as e:
            print(f"Error: {e}")
        print("\n" + "-" * 40 + "\n")

if __name__ == "__main__":
    run_tests()