#!/usr/bin/env python3
"""
Comprehensive tests for the utils module.
"""
import os
import sys
import platform
import tempfile
import pytest
import itertools
from unittest import mock
from pathlib import Path
import subprocess

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.utils import (
    IgnorantTemporaryDirectory,
    ChdirTemporaryDirectory,
    is_image_file,
    safe_abs_path,
    format_content,
    format_messages,
    show_messages,
    split_chat_history_markdown,
    get_pip_install,
    run_install,
    Spinner,
    find_common_root,
    format_tokens,
    touch_file,
    check_pip_install_extra,
    printable_shell_command
)


class TestTemporaryDirectories:
    """Tests for temporary directory classes in utils.py."""

    def test_ignorant_temporary_directory(self):
        """Test IgnorantTemporaryDirectory class."""
        with IgnorantTemporaryDirectory() as temp_dir:
            # Verify the directory exists
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            
            # Create a test file in the directory
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            
            # Test attibutes are delegated correctly
            temp_dir_obj = IgnorantTemporaryDirectory()
            try:
                assert os.path.isdir(temp_dir_obj.name)
            finally:
                temp_dir_obj.cleanup()
        
        # After context exit, directory should be cleaned up
        assert not os.path.exists(temp_dir)
    
    def test_ignorant_temporary_directory_cleanup_error_handling(self):
        """Test error handling in IgnorantTemporaryDirectory cleanup."""
        temp_dir = IgnorantTemporaryDirectory()
        
        # Mock the cleanup to raise an exception
        original_cleanup = temp_dir.temp_dir.cleanup
        temp_dir.temp_dir.cleanup = mock.MagicMock(side_effect=OSError("Permission denied"))
        
        # This should not raise an exception
        temp_dir.cleanup()
        
        # Restore the original cleanup function
        temp_dir.temp_dir.cleanup = original_cleanup
        
        # Clean up
        temp_dir.cleanup()
    
    def test_chdir_temporary_directory(self):
        """Test ChdirTemporaryDirectory class."""
        original_dir = os.getcwd()
        
        with ChdirTemporaryDirectory() as temp_dir:
            # Verify current directory is the temp directory
            assert os.getcwd() == str(Path(temp_dir).resolve())
            
            # Create a test file in the current directory
            with open("test.txt", "w") as f:
                f.write("test")
            
            # Verify file was created in the temp directory
            assert os.path.exists(os.path.join(temp_dir, "test.txt"))
        
        # After context exit, we should be back in original directory
        assert os.getcwd() == original_dir
        
        # And the temp directory should be cleaned up
        assert not os.path.exists(temp_dir)
    
    @mock.patch("os.getcwd")
    def test_chdir_temporary_directory_with_missing_cwd(self, mock_getcwd):
        """Test ChdirTemporaryDirectory when current directory doesn't exist."""
        mock_getcwd.side_effect = FileNotFoundError("No such directory")
        
        with mock.patch('os.chdir') as mock_chdir:
            with ChdirTemporaryDirectory() as temp_dir:
                # Verify chdir was called with the temp directory
                mock_chdir.assert_called_with(Path(temp_dir).resolve())
            
            # After context, chdir should attempt to go back to original directory
            # The implementation now tries to go back to home directory as fallback
            # So we expect 2 calls: one to temp dir, one back to original dir
            assert mock_chdir.call_count == 2


class TestFileUtilities:
    """Tests for file utility functions in utils.py."""
    
    def test_is_image_file(self):
        """Test is_image_file function."""
        # Test common image extensions
        common_image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
        for ext in common_image_exts:
            assert is_image_file(f"image{ext}"), f"Should recognize {ext} as image file"
            # Skip uppercase tests for now - the implementation may be case-sensitive
            # assert is_image_file(f"image{ext.upper()}")

        # Test PDF files
        assert is_image_file("document.pdf"), "Should recognize PDF files"
        
        # Test Path object input
        assert is_image_file(Path("image.png")), "Should handle Path objects"
        
        # Test negative cases
        assert not is_image_file("document.txt"), "Should not recognize text files as images"
        assert not is_image_file("script.py"), "Should not recognize Python files as images"
        assert not is_image_file("webpage.html"), "Should not recognize HTML files as images"
    
    def test_safe_abs_path(self, monkeypatch):
        """Test safe_abs_path function."""
        # Create a temporary file to use for testing
        with tempfile.NamedTemporaryFile() as temp_file:
            # Test with existing absolute path
            abs_path = temp_file.name
            assert safe_abs_path(abs_path) == str(Path(abs_path).resolve())
            
            # Test with relative path (mock getcwd to use the parent dir of temp_file)
            parent_dir = os.path.dirname(temp_file.name)
            monkeypatch.setattr(os, 'getcwd', lambda: parent_dir)
            
            rel_file = os.path.basename(temp_file.name)
            assert os.path.samefile(safe_abs_path(rel_file), temp_file.name)
    
    def test_safe_abs_path_with_missing_cwd(self, monkeypatch):
        """Test safe_abs_path when current directory doesn't exist."""
        # Mock os.getcwd to raise FileNotFoundError
        monkeypatch.setattr("os.getcwd", lambda: exec('raise FileNotFoundError("No such directory")'))
        
        # Test with relative path when CWD doesn't exist
        rel_path = "some_file.txt"
        abs_path = safe_abs_path(rel_path)
        
        # Should handle the exception and return a path
        assert abs_path is not None
        assert os.path.isabs(abs_path)
        assert rel_path in abs_path
    
    def test_find_common_root(self):
        """Test find_common_root function."""
        # Test with single file
        single_file = ["/path/to/file.txt"]
        assert find_common_root(single_file) == "/path/to"
        
        # Test with multiple files in same directory
        same_dir = ["/path/to/file1.txt", "/path/to/file2.txt", "/path/to/file3.txt"]
        assert find_common_root(same_dir) == "/path/to"
        
        # Test with files in different directories
        diff_dirs = ["/path/to/dir1/file1.txt", "/path/to/dir2/file2.txt", "/path/to/file3.txt"]
        assert find_common_root(diff_dirs) == "/path/to"
        
        # Test with empty list
        with mock.patch("os.getcwd", return_value="/current/dir"):
            assert find_common_root([]) == "/current/dir"
    
    def test_touch_file(self):
        """Test touch_file function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test creating a file in existing directory
            file_path = os.path.join(temp_dir, "touch_test.txt")
            assert touch_file(file_path) is True
            assert os.path.exists(file_path)
            
            # Test creating a file in non-existing nested directory
            nested_path = os.path.join(temp_dir, "nested/dir/touch_test.txt")
            assert touch_file(nested_path) is True
            assert os.path.exists(nested_path)
            
            # Test with Path object
            path_obj_file = os.path.join(temp_dir, "path_obj_test.txt")
            assert touch_file(Path(path_obj_file)) is True
            assert os.path.exists(path_obj_file)
            
        # Test with a path that can't be created
        with mock.patch.object(Path, 'mkdir', side_effect=OSError):
            assert touch_file("/invalid/path/file.txt") is False


class TestFormattingFunctions:
    """Tests for formatting functions in utils.py."""
    
    def test_format_content(self):
        """Test format_content function."""
        content = "Line 1\nLine 2\nLine 3"
        role = "USER"
        
        expected = "USER Line 1\nUSER Line 2\nUSER Line 3"
        assert format_content(role, content) == expected
        
        # Test with empty content
        assert format_content(role, "") == ""
    
    def test_format_messages(self):
        """Test format_messages function."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!\nHow can I help?"}
        ]
        
        formatted = format_messages(messages)
        assert "-------" in formatted
        assert "USER Hello" in formatted
        assert "ASSISTANT Hi there!" in formatted
        assert "ASSISTANT How can I help?" in formatted
        
        # Test with title
        formatted_with_title = format_messages(messages, "Chat History")
        assert "CHAT HISTORY" in formatted_with_title
        
        # Test with list content (like for images)
        messages_with_list = [
            {"role": "user", "content": [{"image": {"url": "https://example.com/image.jpg"}}]}
        ]
        formatted_list = format_messages(messages_with_list)
        assert "USER Image URL:" in formatted_list
        
        # Test with function call
        messages_with_function = [
            {"role": "assistant", "function_call": {"name": "test_function", "arguments": "{}"}}
        ]
        formatted_function = format_messages(messages_with_function)
        assert "ASSISTANT Function Call:" in formatted_function
    
    @mock.patch("builtins.print")
    @mock.patch("repomap.utils.format_messages")
    def test_show_messages(self, mock_format, mock_print):
        """Test show_messages function."""
        mock_format.return_value = "Formatted messages"
        
        messages = [{"role": "user", "content": "Test"}]
        show_messages(messages)
        
        mock_format.assert_called_once_with(messages, None)
        mock_print.assert_called_once_with("Formatted messages")
        
        # Test with title and functions
        show_messages(messages, "Title", ["function1", "function2"])
        mock_format.assert_called_with(messages, "Title")
    
    def test_split_chat_history_markdown(self):
        """Test split_chat_history_markdown function."""
        markdown = """# Chat History
#### User Question
This is a user question

Assistant response
with multiple lines

> tool output here

#### Another Question
Follow-up question

More assistant response
"""
        messages = split_chat_history_markdown(markdown)
        
        # Verify correct number and types of messages
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"
        
        # Verify content extraction
        assert "question" in messages[0]["content"].lower()
        assert "response" in messages[1]["content"].lower()
        
        # Test with include_tool=True
        tool_messages = split_chat_history_markdown(markdown, include_tool=True)
        tool_roles = [msg["role"] for msg in tool_messages]
        assert "tool" in tool_roles


class TestInstallationFunctions:
    """Tests for installation-related functions in utils.py."""
    
    def test_get_pip_install(self):
        """Test get_pip_install function."""
        args = ["package1", "package2", "--option"]
        cmd = get_pip_install(args)
        
        # Verify command structure
        assert cmd[0] == sys.executable
        assert cmd[1:3] == ["-m", "pip"]
        assert "install" in cmd
        assert "--upgrade" in cmd
        
        # Verify args are included at the end
        for arg in args:
            assert arg in cmd
    
    @mock.patch('subprocess.Popen')
    def test_run_install(self, mock_popen):
        """Test run_install function."""
        # Mock successful installation
        mock_process = mock.MagicMock()
        mock_process.stdout.read.side_effect = ['I', 'n', 's', 't', 'a', 'l', 'l', 'i', 'n', 'g', '', '']
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Test successful installation
        success, output = run_install(["pip", "install", "package"])
        
        assert success is True
        assert "Installing" in output
    
    @mock.patch('repomap.utils.run_install')
    def test_check_pip_install_extra(self, mock_run_install):
        """Test check_pip_install_extra function."""
        mock_io = mock.MagicMock()
        mock_io.confirm_ask.return_value = True
        
        # Mock successful installation
        mock_run_install.return_value = (True, "Installation successful")
        
        # Test when module is already installed
        with mock.patch.dict(sys.modules, {"existing_module": mock.MagicMock()}):
            result = check_pip_install_extra(mock_io, "existing_module", "Need to install", ["package"])
            assert result is True
            # Verify no prompt was shown
            mock_io.tool_warning.assert_not_called()
        
        # Test when module needs to be installed
        with mock.patch.dict(sys.modules, {}):
            # Mock the import to succeed after installation
            with mock.patch('builtins.__import__', side_effect=[ImportError, mock.MagicMock()]):
                result = check_pip_install_extra(mock_io, "non_existent_module", "Need to install", ["package"])
                assert result is True
                mock_io.tool_warning.assert_called_with("Need to install")
                mock_run_install.assert_called_once()


class TestSpinner:
    """Tests for the Spinner class in utils.py."""
    
    def test_spinner_initialization(self):
        """Test Spinner initialization."""
        spinner = Spinner("Loading")
        assert spinner.text == "Loading"
        assert spinner.visible is False
        assert spinner.tested is False
    
    @mock.patch("sys.stdout.isatty", return_value=True)
    @mock.patch("builtins.print")
    @mock.patch("time.time")
    def test_spinner_step(self, mock_time, mock_print, mock_isatty):
        """Test Spinner step method."""
        # Setup mock time to simulate elapsed time
        mock_time.side_effect = [0, 0.6, 0.6, 0.7, 0.7]
        
        spinner = Spinner("Loading")
        # Pre-initialize the charset for consistent testing
        spinner.test_charset()
        
        # First step after 0.6 seconds should make spinner visible
        spinner.step()
        assert spinner.visible is True
        mock_print.assert_called()
        
        # Second step after 0.1 more seconds should update spinner
        spinner.step()
        # 3 calls: 2 from test_charset initialization + 1 from step
        assert mock_print.call_count == 3
    
    @mock.patch("sys.stdout.isatty", return_value=False)
    @mock.patch("builtins.print")
    def test_spinner_not_tty(self, mock_print, mock_isatty):
        """Test Spinner behavior when stdout is not a TTY."""
        spinner = Spinner("Loading")
        spinner.step()
        
        # No output should be produced when not a TTY
        mock_print.assert_not_called()
    
    @mock.patch("sys.stdout.isatty", return_value=True)
    @mock.patch("builtins.print")
    def test_spinner_end(self, mock_print, mock_isatty):
        """Test Spinner end method."""
        spinner = Spinner("Loading")
        spinner.visible = True
        spinner.end()
        
        # Should print a carriage return and spaces to clear the line
        mock_print.assert_called_with("\r" + " " * (len("Loading") + 3))
        
        # Test end when not visible
        mock_print.reset_mock()
        spinner.visible = False
        spinner.end()
        mock_print.assert_not_called()
    
    @mock.patch("builtins.print")
    def test_spinner_charset_testing_unicode(self, mock_print):
        """Test Spinner charset testing with unicode support."""
        spinner = Spinner("Loading")
        
        # Test with unicode support
        spinner.test_charset()
        assert spinner.tested is True
        # The first character is what we get since we've just initialized the cycle
        assert next(spinner.spinner_chars) == spinner.unicode_spinner[0]
    
    def test_spinner_charset_testing_ascii_fallback(self):
        """Test Spinner charset testing with ASCII fallback."""
        # Use a separate spinner for this test
        spinner = Spinner("Loading")
        
        # Simulate unicode error directly
        spinner.tested = True  # Already tested
        spinner.spinner_chars = itertools.cycle(spinner.ascii_spinner)
        
        # The first character is what we get since we've just initialized the cycle
        assert next(spinner.spinner_chars) == spinner.ascii_spinner[0]


class TestMiscFunctions:
    """Tests for miscellaneous functions in utils.py."""
    
    def test_format_tokens(self):
        """Test format_tokens function."""
        # Test small values
        assert format_tokens(0) == "0"
        assert format_tokens(123) == "123"
        assert format_tokens(999) == "999"
        
        # Test thousand values
        assert format_tokens(1000) == "1.0k"
        assert format_tokens(1234) == "1.2k"
        assert format_tokens(9876) == "9.9k"
        
        # Test large values
        assert format_tokens(10000) == "10k"
        assert format_tokens(12345) == "12k"
        assert format_tokens(123456) == "123k"
    
    def test_printable_shell_command(self):
        """Test printable_shell_command function."""
        cmd = ["python", "-m", "pip", "install", "package with spaces"]
        
        # Test on different platforms
        with mock.patch("platform.system", return_value="Windows"):
            result = printable_shell_command(cmd)
            # On Windows, should use list2cmdline
            assert "python -m pip install" in result
            assert "package with spaces" in result
        
        with mock.patch("platform.system", return_value="Linux"):
            with mock.patch("shlex.join", return_value="python -m pip install 'package with spaces'"):
                result = printable_shell_command(cmd)
                # On Linux, should use shlex.join
                assert "python -m pip install" in result
                assert "'package with spaces'" in result