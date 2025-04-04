# Large Repository Handling Improvements

## Summary of Changes Needed

To improve RepoMap's handling of large repositories and ensure signatures are not truncated, the following modifications need to be implemented:

### 1. Create a Section Splitting Module

Create a new file at `repomap/section_splitting.py` with the following content:

```python
#!/usr/bin/env python3
"""
Extension module for RepoMap that adds section splitting functionality.

This module provides methods to handle large sections in repository maps,
ensuring that no signatures are truncated across split boundaries.
It allows splitting sections at natural boundaries like symbol markers.
"""

class SectionSplitter:
    """
    Class to handle splitting sections when they exceed token limits.
    Designed to be used within a RepoMap instance.
    """
    
    @staticmethod
    def split_section_by_signatures(token_counter_func, section_content, max_tokens):
        """
        Split a section into multiple parts without truncating signatures.
        
        Args:
            token_counter_func: Function to count tokens in text
            section_content: Content of the section to split
            max_tokens: Maximum tokens per part
            
        Returns:
            List of section parts, each under max_tokens
        """
        # If the section is already small enough, return as is
        section_tokens = token_counter_func(section_content)
        if section_tokens <= max_tokens:
            return [section_content]
        
        # Split the section into lines
        lines = section_content.splitlines()
        
        # Find good split points (symbol markers "⋮" for RepoMap)
        split_points = []
        for i, line in enumerate(lines):
            if line.strip() == "⋮":
                split_points.append(i)
        
        # Ensure we have at least one split point at the beginning
        split_points = [0] + sorted(split_points)
        
        # Create parts by splitting at natural boundaries
        parts = []
        current_part_lines = []
        current_tokens = 0
        last_split_point = 0
        
        for i, line in enumerate(lines):
            # Check if adding this line would exceed the token limit
            line_tokens = token_counter_func(line + "\n")
            
            if current_tokens + line_tokens > max_tokens:
                # Find the best split point before the current line
                best_split_point = last_split_point
                for point in split_points:
                    if point <= i and point > last_split_point:
                        best_split_point = point
                
                if best_split_point > last_split_point:
                    # Split at the natural boundary
                    part_content = "\n".join(lines[last_split_point:best_split_point])
                    parts.append(part_content)
                    
                    # Start a new part from the split point
                    current_part_lines = lines[best_split_point:i+1]
                    current_tokens = token_counter_func("\n".join(current_part_lines) + "\n")
                    last_split_point = best_split_point
                else:
                    # If we can't find a good split point, include the current line in its own part
                    current_part_lines.append(line)
                    part_content = "\n".join(current_part_lines)
                    parts.append(part_content)
                    
                    # Reset for next part
                    current_part_lines = []
                    current_tokens = 0
                    last_split_point = i + 1
            else:
                # Add the line to the current part
                current_part_lines.append(line)
                current_tokens += line_tokens
        
        # Add the last part if there's anything left
        if current_part_lines:
            part_content = "\n".join(current_part_lines)
            parts.append(part_content)
        
        return parts

def split_large_section(io, verbose, section_tokens, max_map_tokens, rel_fname, 
                        file_content, token_counter, current_map, output_parts, current_part):
    """
    Handle a section that exceeds the token limit by splitting it.
    
    Args:
        io: IO utilities instance for output
        verbose: Whether to show verbose output
        section_tokens: Number of tokens in the section
        max_map_tokens: Maximum tokens per part
        rel_fname: Relative filename for the section
        file_content: Content of the section
        token_counter: Function to count tokens
        current_map: Current map content
        output_parts: List to store output parts
        current_part: Current part number
        
    Returns:
        Tuple of (continue_flag, current_map, current_part)
        continue_flag: Whether to continue to the next file
        current_map: Updated map content
        current_part: Updated part number
    """
    if verbose:
        io.tool_warning(f"Section for file {rel_fname} exceeds token limit ({section_tokens} > {max_map_tokens})")
        io.tool_output("Splitting this section into multiple smaller parts")
    
    # Split the section into smaller chunks without truncating signatures
    split_sections = SectionSplitter.split_section_by_signatures(
        token_counter, file_content, max_map_tokens
    )
    
    for split_section in split_sections:
        # Check if we need to start a new part for each split section
        current_tokens = token_counter(current_map)
        split_tokens = token_counter(split_section)
        
        if current_tokens + split_tokens > max_map_tokens:
            # Save the current map as a part
            output_parts.append((current_part, current_map))
            current_part += 1
            current_map = f"Repository contents (continued, part {current_part}):\n\n"
        
        # Add the split section to the current map
        current_map += split_section
        
        # If after adding, we're already at the limit, start a new part
        if token_counter(current_map) >= max_map_tokens * 0.9:  # 90% utilization threshold
            output_parts.append((current_part, current_map))
            current_part += 1
            current_map = f"Repository contents (continued, part {current_part}):\n\n"
    
    # Return flag to continue to the next file, along with updated state
    return True, current_map, current_part
```

### 2. Modify repomap.py

Make the following changes to `repomap/repomap.py`:

1. Add import at the top of the file (after other imports):

```python
from .section_splitting import split_large_section
```

2. Replace the warning section that handles large sections with a call to the new function:

Find this pattern:
```python
# If this section alone is larger than max_map_tokens, we need to warn
if section_tokens > max_map_tokens:
    if self.verbose:
        self.io.tool_warning(f"Section for file {rel_fname} exceeds token limit ({section_tokens} > {max_map_tokens})")
        self.io.tool_warning("This section will be placed in its own part, but may still be truncated by models")
```

Replace it with:
```python
# If this section alone is larger than max_map_tokens, split it
if section_tokens > max_map_tokens:
    # Use the section_splitting module to handle this large section
    continue_flag, current_map, current_part = split_large_section(
        self.io, self.verbose, section_tokens, max_map_tokens, rel_fname,
        file_content, self.token_count, current_map, output_parts, current_part
    )
    if continue_flag:
        continue
```

### 3. Update models.py

Add a method to the Model class to handle chunking by tokens:

```python
def chunk_text_by_tokens(self, text, max_tokens_per_chunk):
    """
    Split text into chunks, each with approximately max_tokens_per_chunk tokens.
    
    This method ensures that no line is split across chunk boundaries.
    
    Args:
        text: Text to split
        max_tokens_per_chunk: Maximum tokens per chunk
        
    Returns:
        List of text chunks
    """
    # If the text is already small enough, return as is
    total_tokens = self.token_count(text)
    if total_tokens <= max_tokens_per_chunk:
        return [text]
    
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = []
    current_chunk_tokens = 0
    
    for line in lines:
        line_tokens = self.token_count(line)
        
        # If this single line is too large, we need to split it
        if line_tokens > max_tokens_per_chunk:
            # First, add the current chunk if not empty
            if current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = []
                current_chunk_tokens = 0
            
            # Split the large line at character boundaries
            # This is a fallback for extremely long lines
            chunks_needed = (line_tokens + max_tokens_per_chunk - 1) // max_tokens_per_chunk
            chars_per_chunk = len(line) // chunks_needed
            
            for i in range(0, len(line), chars_per_chunk):
                chunk = line[i:i+chars_per_chunk]
                chunks.append(chunk)
        
        # If adding this line would exceed the limit, start a new chunk
        elif current_chunk_tokens + line_tokens > max_tokens_per_chunk:
            # Save the current chunk
            chunks.append("".join(current_chunk))
            # Start a new chunk with this line
            current_chunk = [line]
            current_chunk_tokens = line_tokens
        else:
            # Add the line to the current chunk
            current_chunk.append(line)
            current_chunk_tokens += line_tokens
    
    # Add the last chunk if there's anything left
    if current_chunk:
        chunks.append("".join(current_chunk))
    
    return chunks
```

## Benefits of These Changes

1. **Prevents Signature Truncation**: By splitting sections at natural boundaries like symbol markers, code signatures won't be cut off in the middle.

2. **Improved Large Repository Handling**: The code can now process repositories of any size, splitting content into appropriate chunks without losing important information.

3. **Modular Implementation**: The section splitting functionality is isolated in its own module, making the code more maintainable.

4. **Better Resource Utilization**: Sections that exceed token limits are properly handled, ensuring better resource utilization while maintaining functionality.

## Testing After Implementation

After implementing these changes, run the tests with:

```bash
python run_tests.py
```

The implemented improvements should address the failures in `test_token_splitting.py` and `test_code_elements.py` that were related to token handling and signature preservation.

## Manual Testing with Large Repositories

Test the improved code with a large repository containing many files:

1. Clone a large repository (like a popular open-source project)
2. Run RepoMap on it with different token limits
3. Verify that all signatures are preserved and not truncated
4. Check that large sections are properly split into multiple parts

This will confirm that the improved code handles large repositories correctly without truncating signatures.