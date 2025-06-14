import pytest
import os
import tempfile
import shutil
from psh.shell import Shell


class TestGlobExpansion:
    
    @pytest.fixture
    def shell(self):
        # Respect PSH_USE_VISITOR_EXECUTOR env var
        import os
        use_visitor = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')
        return Shell(use_visitor_executor=use_visitor)
    
    @pytest.fixture
    def test_dir(self):
        """Create a temporary directory with test files"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files
        test_files = [
            'file1.txt',
            'file2.txt',
            'file3.log',
            'test.py',
            'test_runner.py',
            'README.md',
            'data.json',
            'config.yaml',
            '.hidden',
            'file[1].txt',
            'file{2}.txt'
        ]
        
        for filename in test_files:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write(f"Test content for {filename}\n")
        
        # Create subdirectory with files
        subdir = os.path.join(temp_dir, 'subdir')
        os.makedirs(subdir)
        with open(os.path.join(subdir, 'nested.txt'), 'w') as f:
            f.write("Nested file content\n")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_star_wildcard(self, shell, test_dir, capsys):
        """Test * wildcard expansion"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Test *.txt
            shell.run_command("echo *.txt")
            captured = capsys.readouterr()
            assert "file1.txt" in captured.out
            assert "file2.txt" in captured.out
            assert "file3.log" not in captured.out
            
            # Test file*.txt
            shell.run_command("echo file*.txt")
            captured = capsys.readouterr()
            assert "file1.txt" in captured.out
            assert "file2.txt" in captured.out
            assert "test.py" not in captured.out
            
            # Test *.py
            shell.run_command("echo *.py")
            captured = capsys.readouterr()
            assert "test.py" in captured.out
            assert "test_runner.py" in captured.out
            assert "file1.txt" not in captured.out
            
        finally:
            os.chdir(old_cwd)
    
    def test_question_mark_wildcard(self, shell, test_dir, capsys):
        """Test ? wildcard expansion"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Test file?.txt
            shell.run_command("echo file?.txt")
            captured = capsys.readouterr()
            assert "file1.txt" in captured.out
            assert "file2.txt" in captured.out
            assert "file3.log" not in captured.out
            
            # Test ????.py
            shell.run_command("echo ????.py")
            captured = capsys.readouterr()
            assert "test.py" in captured.out
            assert "test_runner.py" not in captured.out
            
        finally:
            os.chdir(old_cwd)
    
    def test_bracket_wildcard(self, shell, test_dir, capsys):
        """Test [...] wildcard expansion"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Test file[12].txt
            shell.run_command("echo file[12].txt")
            captured = capsys.readouterr()
            assert "file1.txt" in captured.out
            assert "file2.txt" in captured.out
            assert "file3.log" not in captured.out
            
            # Test [Rt]*.md
            shell.run_command("echo [Rt]*.md")
            captured = capsys.readouterr()
            assert "README.md" in captured.out
            
        finally:
            os.chdir(old_cwd)
    
    def test_no_matches(self, shell, test_dir, capsys):
        """Test behavior when no files match the pattern"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Pattern with no matches should return literal string
            shell.run_command("echo *.nonexistent")
            captured = capsys.readouterr()
            assert "*.nonexistent" in captured.out
            
            shell.run_command("echo no_such_file_*")
            captured = capsys.readouterr()
            assert "no_such_file_*" in captured.out
            
        finally:
            os.chdir(old_cwd)
    
    def test_quoted_globs_not_expanded(self, shell, test_dir, capsys):
        """Test that quoted glob patterns are not expanded"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Single quotes
            shell.run_command("echo '*.txt'")
            captured = capsys.readouterr()
            assert captured.out.strip() == "*.txt"
            
            # Double quotes
            shell.run_command('echo "*.txt"')
            captured = capsys.readouterr()
            assert captured.out.strip() == "*.txt"
            
        finally:
            os.chdir(old_cwd)
    
    def test_multiple_globs_in_command(self, shell, test_dir, capsys):
        """Test multiple glob patterns in a single command"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            shell.run_command("echo *.txt *.py")
            captured = capsys.readouterr()
            assert "file1.txt" in captured.out
            assert "file2.txt" in captured.out
            assert "test.py" in captured.out
            assert "test_runner.py" in captured.out
            
        finally:
            os.chdir(old_cwd)
    
    def test_glob_with_subdirectories(self, shell, test_dir, capsys):
        """Test glob patterns with subdirectories"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            shell.run_command("echo subdir/*.txt")
            captured = capsys.readouterr()
            assert "subdir/nested.txt" in captured.out
            
            shell.run_command("echo */nested.txt")
            captured = capsys.readouterr()
            assert "subdir/nested.txt" in captured.out
            
        finally:
            os.chdir(old_cwd)
    
    def test_glob_in_pipeline(self, shell, test_dir):
        """Test glob expansion in pipelines"""
        import tempfile
        
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        # Create temporary file for output capture
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            temp_file = f.name
        
        try:
            # Glob expansion should work in pipelines
            result = shell.run_command(f"ls *.txt | wc -l > {temp_file}")
            assert result == 0
            
            with open(temp_file, 'r') as f:
                output = f.read().strip()
            # file1.txt, file2.txt, file[1].txt, file{2}.txt = 4 files
            assert output == "4"
            
        finally:
            os.chdir(old_cwd)
            os.unlink(temp_file)
    
    def test_glob_sorting(self, shell, test_dir, capsys):
        """Test that glob results are sorted"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            shell.run_command("echo file*.txt")
            captured = capsys.readouterr()
            # Results should be in sorted order
            output = captured.out.strip()
            files = output.split()
            assert files == sorted(files)
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.skip(reason="Escape handling for globs is complex and not implemented yet")
    def test_escaped_globs(self, shell, test_dir, capsys):
        """Test that escaped glob patterns are not expanded"""
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Test backslash escaping
            shell.run_command(r"echo \*.txt")
            captured = capsys.readouterr()
            # Should show literal *.txt without the backslash
            assert captured.out.strip() == "*.txt"
            
            # Test escaping specific characters
            shell.run_command(r"echo file\?.txt")
            captured = capsys.readouterr()
            assert captured.out.strip() == "file?.txt"
            
        finally:
            os.chdir(old_cwd)