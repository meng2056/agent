import os
import stat
import shutil
import magic
import chardet
from langchain_core.tools import tool
from pathlib import Path
from typing import Literal

BINARY_FILE_EXTENTSIONS = {
    ".exe", ".dll", '.so', '.bin', '.zip', '.tar', '.gz', '.bz2',
    '.7z', '.rar', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.bmp',
    '.mp3', '.mp4', '.avi', '.mov', '.flac', '.wav'
}

CODE_FILE_EXTENTSIONS = {
    ".py", ".c", ".c", ".il", ".java", ".v", ".sv"
}

DEFAULT_MAX_FILE_SIZE = 200 * 1024


def _is_binary_file(file_path: str) -> bool:
    path_p = Path(file_path)
    file_ext = path_p.suffix.lower()
    if file_ext in BINARY_FILE_EXTENTSIONS:
        return True

    # use magic to judge
    try:
        mime = magic.from_file(file_path, mime=True)
        return not mime.startswith('text/')
    except:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
        return b'\x00' in chunk


def detect_file_encoding(file_path: str) -> str:
    """
    Detect the encoding of a file.
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)

    result = chardet.detect(raw_data)
    return result['encoding'] or 'utf-8'


def smart_truncate(
        content: str,
        max_length: int,
        file_ext: str = None
) -> tuple[str, bool]:
    """
    Truncate a string to a specified length, preserving semantic integrity.
    """
    if len(content) < max_length:
        return content, False

    if file_ext in CODE_FILE_EXTENTSIONS:
        delimiters = ['\n\n', '\ndef', '\nclass', '\nstruct', '\nfunc',
                      '\nmodule', '\nclass', '\nfunction', '\nwhile']
    elif file_ext in ['.md', '.rpt', '.txt', '.rst']:
        delimiters = ['. ', '! ', '? ', '! ', '; ', '\n\n', '\n']

    else:
        delimiters = ['\n\n', '\n']

    trunc_pos = max_length
    for delimiter in delimiters:
        pos = content.rfind(delimiter, 0, max_length)
        if pos != -1:
            trunc_pos = pos + len(delimiter)
            break

    if trunc_pos == max_length:
        trunc_pos = max_length

    truncated = content[:trunc_pos]

    return (f"{truncated}\n\n[CONTENT_TRUNCATED: {trunc_pos}/{len(content)} "
            f"bytes. To read more, request the full file or specify a "
            f"starting position to continue Reading.]"), True


@tool
def get_current_dir() -> str:
    """
    Get the current working directory.
    """
    return str(Path.cwd())


@tool
def change_dir(path: str) -> str:
    """
    Change the current working directory to the specified path.
    Args:
      path(str, required): The target directory path(absolute path)
    Returns:
        str: A message indicating success or failure, including the new
             current directory.
    Example:
      >>> change_dir('/home/barwellg')
      "Changed directory to /home/barwellg"
    """
    try:
        os.chdir(path)
        return f"Changed directory to {Path.cwd()}."
    except FileNotFoundError:
        return f"Error: Directory '{path}' does not exist"
    except PermissionError:
        return f"Error: Permission denied to access '{path}'"
    except Exception as e:
        return f"Error: Failed to change directory: {str(e)}"


@tool
def list_directory(
        path: str,
        content_type: Literal["all", "files", "dirs"] = "all"
) -> str:
    """
    List files and/or directories in the specified path.
    Args:
      path(str, required): The directory path to list.(absolute path)
      content_type(str, optional): Choose which type of contents to list.
        - 'all': default value, will list all files and directories just under
                 path.
        - 'files': will only list all files just under specified path.
        - 'dirs': will only list all directories under specified path.
    Returns:
      str: A formatted string listing the contents or an error message.

    """
    try:
        entries = os.listdir(path)
        if content_type == "files":
            entries = [e for e in entries
                       if os.path.isfile(os.path.join(path, e))]
        elif content_type == "dirs":
            entries = [e for e in entries
                       if os.path.isdir(os.path.join(path, e))]
        if not entries:
            return f"No {content_type} found in {path}"

        return f"{content_type.capitalize()} in {path}: {', '.join(entries)}"

    except FileNotFoundError:
        return f"Error: Directory '{path}' does not exist"
    except PermissionError:
        return f"Error: Permission denied to access '{path}'"
    except Exception as e:
        return f"Error: Failed to list directory: {str(e)}"


@tool
def copy_file(src_path: str, dest_path: str) -> str:
    """
    Copy a file from src_path to dest_path.
    Args:
      src_path(str, required): The source file path.(absolute_path)
      dest_path(str, required): The destination file path or directory.(absolute_path)
    Returns:
      str: A message indicating success or failure.
    """
    try:
        shutil.copy2(src_path, dest_path)
        return f"File successfully copied from `{src_path}` to `{dest_path}"
    except FileNotFoundError:
        return (f"Error: Source file `{src_path}` or destination `{dest_path}`"
                f"does not exist!")
    except PermissionError:
        return (f"Error: Permission denied for copying `{src_path}` to "
                f"`{dest_path}`.")
    except Exception as e:
        return f"Error: Failed to copy file: {str(e)}"


@tool
def move_file(src_path: str, dest_path: str) -> str:
    """
    move a file from src_path to dest_path.
    Args:
      src_path(str, required): The source file path.(absolute path)
      dest_path(str, required): The destination file path or directory.(absolute_path)
    Returns:
      str: A message indicating success or failure.
    """
    try:
        shutil.move(src_path, dest_path)
        return f"File successfully moved from `{src_path}` to ``{dest_path}"
    except FileNotFoundError:
        return (f"Error: Source file `{src_path}` or destination `{dest_path}`"
                f"does not exist!")
    except PermissionError:
        return (f"Error: Permission denied for moving `{src_path}` to "
                f"`{dest_path}`.")
    except Exception as e:
        return f"Error: Failed to move file: {str(e)}"


@tool
def create_dir(path: str) -> str:
    """
    Create a directory at the specified path.
    Args:
      path(str): The directory path to create(absolute path).
    Returns:
      str: A message indicating success or failure
    Example:

    """
    try:
        os.makedirs(path, exist_ok=True)
        return f"Directory created successfully at `{path}`"
    except PermissionError:
        return f"Error: PermissionDenied to create directory '{path}'"
    except Exception as e:
        return f"Error: Failed to create directory: {str(e)}"


@tool
def delete_file_dir(path: str) -> str:
    """
    Delete a file or directory at the specified path.
    Args:
      path(str): The file or directory path to delete(absolute path).
    Returns:
      str: A message indicating success or failure
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
            return f"File deleted successfully at `{path}`"
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return f"Directory deleted successfully at `{path}`"
        else:
            return (f"Error: Path `{path}` does not exist or is not a file "
                    f"or directory.")
    except PermissionError:
        return f"Error: Permission denied to delete '{path}'"
    except Exception as e:
        return f"Error: Failed to delete file or directory: {str(e)}"


@tool
def check_exist(path: str) -> str:
    """
    Check if a file or directory exists at the specified path.
    Args:
      path(str): The file or directory path to check.(absolute path)
    Returns:
      str: A message indicating whether the path exists and its type.

    """
    try:
        if os.path.exists(path):
            if os.path.isfile(path):
                return f"File exists at `{path}`"
            elif os.path.isdir(path):
                return f"Directory exists at `{path}`"
        return f"Path `{path}` does not exist or is not a file or directory."
    except Exception as e:
        return f"Error: Failed to check existance: {str(e)}"


@tool
def get_permissions(path: str) -> str:
    """
    Get the permissions of a file or directory in a human-readable format.
    Args:
      path(str): The file or directory path in absolute way.
    Returns:
      str: A formatted string with permission information (e.g., "Owner: read,
           write; Group: read; Others: read") or an error message.

    """
    try:
        st = os.stat(path)
        file_type = "directory" if os.path.isdir(path) else "file"

        mode = st.st_mode

        def get_permission_str(bits):
            perms = []
            if (bits & stat.S_IRUSR or bits & stat.S_IRGRP
                    or bits & stat.S_IROTH):
                perms.append("read")
            if (bits & stat.S_IWUSR or bits & stat.S_IWGRP
                    or bits & stat.S_IWOTH):
                perms.append("write")
            if (bits & stat.S_IXUSR or bits & stat.S_IXGRP
                    or bits & stat.S_IXOTH):
                perms.append("execute")
            return ", ".join(perms) if perms else "none"

        owner_perms = get_permission_str(mode & (stat.S_IRUSR |
                                                 stat.S_IWUSR |
                                                 stat.S_IXUSR))
        group_perms = get_permission_str(
            mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP))

        others_perms = get_permission_str(
            mode & (stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH))

        return (f"Permissions for {file_type} at `{path}`:\n"
                f"Owner: {owner_perms}\n"
                f"Group: {group_perms}\n"
                f"Others: {others_perms}")
    except FileNotFoundError:
        return f"Error: Path `{path}` does not exist!"
    except PermissionError:
        return f"Error: Permission denied to access `{path}`)"
    except Exception as e:
        return f"Error: Failed to get permissions: {str(e)}"


@tool
def read_tool(
        file_path: str,
        max_size: int = DEFAULT_MAX_FILE_SIZE,
        start_pos: int = 0,
        encoding: str = None
) -> str | None:
    """
    Reads text file content with intelligent processing capabilities,
    avoiding binary files and excessively large files.

    Functionality Description:
    1. First checks if the file is a binary file; if so, returns a prompt
       message and indicate the read_tool encoutner some ERROR instead of
       reading content
    2. Checks file size; if exceeding the specified maximum, intelligently
       truncates content while preserving semantic integrity
    3. Supports reading from a specified position, facilitating continuation
       of truncated files
    4. Automatically detects file encoding, with option to manually specify
       encoding format

    Parameters:
    - file_path(str, Required): path to the file to be read (absolute path or
      relative path from current working directory)
    - max_size(int, Optional): maximum byte limit for file content, default
      200KB
    - start_pos(int, Optional): position to start reading (byte offset),
      default 0 (read from beginning)
    - encoding(str, Optional): file encoding format such as 'utf-8', 'gbk',
      etc. Automatically detected if not specified

    Returns:
    - String containing file content or appropriate prompt messages. If Content
      is truncated, a clear truncation marker will be included:
      [CONTENT_TRUNCATED: bytes_read/total_bytes bytes. To read more, request
      the full file or specify a starting position to continue reading.]
    Notes:
    - Binary files (e.g. images, audio, video, archives) will not be read.
    - Oversized files will be intelligently truncated to avoid breaking
      semantic units like code functions or sentences
    - If start_pos is specified, reading will begin from that position, up
      to max_size bytes
    - Possible errors include: file not found, insufficient permissions, path
      errors, etc., with corresponding error messages returned
    """
    try:
        file_p = Path(file_path)
        if not os.path.exists(file_path):
            return f"read_tool ERROR: File {file_path} not exists."

        if not os.path.isfile(file_path):
            return f"read_tool ERROR: {file_path} is not a file."

        file_size = os.path.getsize(file_path)
        file_ext = file_p.suffix.lower()

        if _is_binary_file(file_path):
            return (f"read_tool ERROR: {file_path} is a binary file, This tool "
                    f"can not read such binary file.")

        if start_pos < 0:
            return (f"read_tool ERROR: the read start position cannot be "
                    f"negative, current position {start_pos}")

        if start_pos > file_size:
            return (f"read_tool ERROR: The read start position {start_pos} is "
                    f"bigger than file size {file_size}.")

        # actually bytes to read.
        bytes_to_read = min(max_size, file_size - start_pos)

        if not encoding:
            try:
                encoding = detect_file_encoding(file_path)
            except Exception as e:
                return (f"read_tool ERROR: Failed to detect file encoding, "
                        f"please specify manually. Error: {e}")

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.seek(start_pos)
                content = f.read(bytes_to_read)
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(start_pos)
                content = f.read(bytes_to_read)
                content = (f"Warning: the file may not encoding in {encoding},"
                           f" Already use utf-8 ignore the read exception.\n "
                           f"The content of the file:\n {content}")
        except Exception as e:
            return (f"read_tool_ERROR: There are something wrong when read the"
                    f" file")

        if start_pos == 0 and file_size > max_size:
            content, truncated = smart_truncate(content, max_size, file_ext)
            if truncated:
                return (f"file: {file_path} has size {file_size} bytes, exceeds"
                        f" the maximum limit of {max_size} bytes, The file "
                        f"content has been intelligently truncated: "
                        f"\n\n{content}")
        elif start_pos > 0:
            if start_pos + bytes_to_read >= file_size:
                return (f"The remaining content of {file_path} has been read "
                        f"starting from position {start_pos}:\n\n"
                        f"{content}\n\n[END_OF_FILE: All content has been "
                        f"read]")
            else:
                return (f"The partial content of {file_path} has been read "
                        f"starting from position {start_pos}(read "
                        f"{bytes_to_read} bytes):\n\n{content}\n\n"
                        f"[CONTENT_CONTINUES: Specify start_pos="
                        f"{start_pos + bytes_to_read} to continue reading the"
                        f"remaining content!]")
        else:
            return (f"The Content of {file_path}(size: {file_size} bytes) is:"
                    f"\n\n{content}")

    except Exception as e:
        return (f"read_tool ERROR: Failed to read file {file_path}. Error: "
                f"{str(e)}")


@tool
def write_file(file_path: str, content: str) -> str:
    """
    Writes the given content to a specified file path.

    This tool creates or overwrites a file at the given `file_path` with the provided `content`.
    It includes basic checks for the existence of the parent directory and handles common
    file writing errors, returning informative messages to the LLM.

    Args:
        file_path (str): The full path to the file to be written (e.g., "data/my_document.txt").
                         The directory must exist if it's not the current working directory.
        content (str): The string content to write into the file.

    Returns:
        str: A success message if the file was written successfully, or an error message
             detailing the issue (e.g., directory not found, permission denied).
    """
    directory = os.path.dirname(file_path)

    # Check if a directory path is specified and if it exists.
    # If directory is an empty string, it means the file is in the current directory,
    # which we assume always exists.
    if directory and not os.path.exists(directory):
        return (f"Error: The directory '{directory}' does not exist. "
                f"Please ensure the parent directory exists before attempting to write the file.")

    try:
        # Use 'w' mode to create or overwrite the file.
        # Specify encoding for wider compatibility, especially with LLM generated content.
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote content to '{file_path}'."
    except PermissionError:
        return (f"Error: Permission denied when trying to write to '{file_path}'. "
                f"The system might not have the necessary permissions for this location.")
    except IOError as e:
        return (f"Error: An I/O error occurred while writing to '{file_path}': {e}. "
                f"This might indicate an issue with the file path or disk.")
    except Exception as e:
        return (f"Error: An unexpected error occurred while writing to '{file_path}': {e}. "
                f"Please check the file path and content for any unusual characters or issues.")
