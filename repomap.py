import colorsys
import glob
import math
import os
import random
import re
import shutil
import sqlite3
import sys
import time
import warnings
from collections import Counter, defaultdict, namedtuple
from importlib import resources
from pathlib import Path

from diskcache import Cache
from grep_ast import TreeContext, filename_to_lang
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from tqdm import tqdm

from dump import dump
from special import filter_important_files
from utils import Spinner

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from grep_ast.tsl import USING_TSL_PACK, get_language, get_parser  # noqa: E402

Tag = namedtuple("Tag", "rel_fname fname line name kind".split())


SQLITE_ERRORS = (sqlite3.OperationalError, sqlite3.DatabaseError, OSError)


CACHE_VERSION = 3
if USING_TSL_PACK:
    CACHE_VERSION = 4


class RepoMap:
    TAGS_CACHE_DIR = f".repomap.tags.cache.v{CACHE_VERSION}"

    warned_files = set()

    def __init__(
        self,
        map_tokens=1024,
        root=None,
        main_model=None,
        io=None,
        repo_content_prefix=None,
        verbose=False,
        max_context_window=None,
        map_mul_no_files=8,
        refresh="auto",
    ):
        self.io = io
        self.verbose = verbose
        self.refresh = refresh

        if not root:
            root = os.getcwd()
        self.root = root

        self.load_tags_cache()
        self.cache_threshold = 0.95

        self.max_map_tokens = map_tokens
        self.map_mul_no_files = map_mul_no_files
        self.max_context_window = max_context_window

        self.repo_content_prefix = repo_content_prefix

        self.main_model = main_model

        self.tree_cache = {}
        self.tree_context_cache = {}
        self.map_cache = {}
        self.map_processing_time = 0
        self.last_map = None

        if self.verbose:
            self.io.tool_output(
                f"RepoMap initialized with map_mul_no_files: {self.map_mul_no_files}"
            )

    def token_count(self, text):
        len_text = len(text)
        if len_text < 200:
            return self.main_model.token_count(text)

        lines = text.splitlines(keepends=True)
        num_lines = len(lines)
        step = num_lines // 100 or 1
        lines = lines[::step]
        sample_text = "".join(lines)
        sample_tokens = self.main_model.token_count(sample_text)
        est_tokens = sample_tokens / len(sample_text) * len_text
        return est_tokens

    def get_repo_map(
        self,
        chat_files,
        other_files,
        mentioned_fnames=None,
        mentioned_idents=None,
        force_refresh=False,
    ):
        """
        Generate a map of the repository, potentially split into multiple files.

        This method will process all files in the repository without any arbitrary
        limits on total size. The output will be split into multiple files if needed,
        each staying under the token limit.

        Args:
            chat_files: Files from the chat context
            other_files: Other files to include
            mentioned_fnames: Filenames mentioned in the chat
            mentioned_idents: Identifiers mentioned in the chat
            force_refresh: Force refresh the cache

        Returns:
            A string containing the repository map (or the first part if split)
        """
        if not other_files and not chat_files:
            return
        if not mentioned_fnames:
            mentioned_fnames = set()
        if not mentioned_idents:
            mentioned_idents = set()

        max_map_tokens = self.max_map_tokens

        # With no files in the chat, give a bigger view of the entire repo
        padding = 4096
        if max_map_tokens and self.max_context_window and not self.max_map_tokens == 1000000:  # Not using --no-split
            target = min(
                int(max_map_tokens * self.map_mul_no_files),
                self.max_context_window - padding,
            )
        else:
            target = max_map_tokens

        if not chat_files and self.max_context_window and target > 0 and not self.max_map_tokens == 1000000:
            max_map_tokens = target

        try:
            # Get the files listing, passing all arguments to get_ranked_tags_map
            files_listing = self.get_ranked_tags_map(
                chat_files,
                other_files,
                max_map_tokens,
                mentioned_fnames,
                mentioned_idents,
                force_refresh,
            )
        except RecursionError:
            self.io.tool_error("Error during repository mapping, trying with a smaller subset")
            # Instead of disabling, try with a smaller subset
            try:
                # Get just the first 1000 files
                reduced_other_files = other_files[:1000] if len(other_files) > 1000 else other_files
                if self.verbose and len(other_files) > 1000:
                    self.io.tool_warning(f"Processing only the first 1000 files out of {len(other_files)}")

                files_listing = self.get_ranked_tags_map(
                    chat_files,
                    reduced_other_files,
                    max_map_tokens,
                    mentioned_fnames,
                    mentioned_idents,
                    force_refresh,
                )
            except Exception as e:
                self.io.tool_error(f"Failed to generate repository map: {str(e)}")
                return

        if not files_listing:
            return

        if self.verbose:
            # Get the total tokens and potentially the split count
            part_files = glob.glob(os.path.join("output", "repomap_*_part*.txt"))
            if part_files and not self.max_map_tokens == 1000000:
                total_tokens = 0
                for part_file in part_files:
                    try:
                        with open(part_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            total_tokens += self.token_count(content)
                    except (IOError, OSError):
                        pass
                self.io.tool_output(f"Repo-map: {total_tokens / 1024:.1f} total k-tokens in {len(part_files)} parts")
            else:
                num_tokens = self.token_count(files_listing)
                self.io.tool_output(f"Repo-map: {num_tokens / 1024:.1f} k-tokens")

        if chat_files:
            other = "other "
        else:
            other = ""

        if self.repo_content_prefix:
            repo_content = self.repo_content_prefix.format(other=other)
        else:
            repo_content = ""

        repo_content += files_listing

        return repo_content

    def get_rel_fname(self, fname):
        try:
            return os.path.relpath(fname, self.root)
        except ValueError:
            # Issue #1288: ValueError: path is on mount 'C:', start on mount 'D:'
            # Just return the full fname.
            return fname

    def tags_cache_error(self, original_error=None):
        """Handle SQLite errors by trying to recreate cache, falling back to dict if needed"""

        if self.verbose and original_error:
            self.io.tool_warning(f"Tags cache error: {str(original_error)}")

        if isinstance(getattr(self, "TAGS_CACHE", None), dict):
            return

        path = Path(self.root) / self.TAGS_CACHE_DIR

        # Try to recreate the cache
        try:
            # Delete existing cache dir
            if path.exists():
                shutil.rmtree(path)

            # Try to create new cache
            new_cache = Cache(path)

            # Test that it works
            test_key = "test"
            new_cache[test_key] = "test"
            _ = new_cache[test_key]
            del new_cache[test_key]

            # If we got here, the new cache works
            self.TAGS_CACHE = new_cache
            return

        except SQLITE_ERRORS as e:
            # If anything goes wrong, warn and fall back to dict
            self.io.tool_warning(
                f"Unable to use tags cache at {path}, falling back to memory cache"
            )
            if self.verbose:
                self.io.tool_warning(f"Cache recreation error: {str(e)}")

        self.TAGS_CACHE = dict()

    def load_tags_cache(self):
        path = Path(self.root) / self.TAGS_CACHE_DIR
        try:
            self.TAGS_CACHE = Cache(path)
        except SQLITE_ERRORS as e:
            self.tags_cache_error(e)

    def save_tags_cache(self):
        pass

    def get_mtime(self, fname):
        try:
            mtime = os.path.getmtime(fname)
            if self.verbose:
                self.io.tool_output(f"File mtime for {fname}: {mtime}")
            return mtime
        except FileNotFoundError:
            self.io.tool_warning(f"File not found error: {fname}")

    def get_tags(self, fname, rel_fname):
        # Check if the file is in the cache and if the modification time has not changed
        file_mtime = self.get_mtime(fname)
        if file_mtime is None:
            return []

        cache_key = fname
        try:
            val = self.TAGS_CACHE.get(cache_key)  # Issue #1308
        except SQLITE_ERRORS as e:
            self.tags_cache_error(e)
            val = self.TAGS_CACHE.get(cache_key)

        if val is not None and val.get("mtime") == file_mtime:
            try:
                return self.TAGS_CACHE[cache_key]["data"]
            except SQLITE_ERRORS as e:
                self.tags_cache_error(e)
                return self.TAGS_CACHE[cache_key]["data"]

        # miss!
        data = list(self.get_tags_raw(fname, rel_fname))

        # Update the cache
        try:
            self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
            self.save_tags_cache()
        except SQLITE_ERRORS as e:
            self.tags_cache_error(e)
            self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}

        return data

    def get_tags_raw(self, fname, rel_fname):
        # Print verbosity level at the start for debugging
        if self.verbose:
            self.io.tool_output(f"Processing file: {fname}")

        # Try to detect the language
        lang = filename_to_lang(fname)
        if not lang:
            if self.verbose:
                self.io.tool_warning(f"Unknown language for file {fname}")

            # Try to guess from file extension
            ext = os.path.splitext(fname)[1].lower()
            # Comprehensive language mapping from extensions
            extension_to_lang = {
                '.js': 'javascript',
                '.jsx': 'javascript',
                '.py': 'python',
                '.java': 'java',
                '.ts': 'typescript',
                '.tsx': 'typescript',
                '.rb': 'ruby',
                '.go': 'go',
                '.c': 'c',
                '.h': 'c',
                '.cpp': 'cpp',
                '.cxx': 'cpp',
                '.cc': 'cpp',
                '.hpp': 'cpp',
                '.hh': 'cpp',
                '.rs': 'rust',
                '.php': 'php',
                '.cs': 'c_sharp',
                '.swift': 'swift',
                '.kt': 'kotlin',
                '.scala': 'scala',
                '.clj': 'clojure',
                '.ex': 'elixir',
                '.exs': 'elixir',
                '.erl': 'erlang',
                '.elm': 'elm',
                '.hs': 'haskell',
                '.ml': 'ocaml',
                '.lua': 'lua',
                '.r': 'r',
                '.json': 'json',
                '.yaml': 'yaml',
                '.yml': 'yaml',
                '.md': 'markdown',
                '.html': 'html',
                '.css': 'css',
                '.scss': 'scss',
                '.sass': 'scss',
                '.xml': 'xml',
                '.sql': 'sql',
                '.sh': 'bash',
                '.bash': 'bash',
                '.dart': 'dart',
                '.d': 'd',
                '.fs': 'fsharp',
                '.groovy': 'groovy',
                '.jl': 'julia',
                '.nim': 'nim',
                '.pl': 'perl',
                '.raku': 'raku',
                '.rkt': 'racket',
                '.scm': 'scheme',
                '.tcl': 'tcl',
                '.v': 'verilog',
                '.vhdl': 'vhdl',
                '.zig': 'zig',
                '.sol': 'solidity',
                '.toml': 'toml',
            }

            # Look up in our mapping
            lang = extension_to_lang.get(ext)

            # If we still can't determine the language, return
            if not lang:
                if self.verbose:
                    self.io.tool_warning(f"Unsupported file extension: {ext}")
                return

            if self.verbose:
                self.io.tool_output(f"Language detected from extension: {lang}")

        if self.verbose:
            self.io.tool_output(f"Detected language: {lang}")

        # Define common variant name mappings to try
        lang_variants = {
            "c_sharp": ["csharp", "c#"],
            "csharp": ["c_sharp", "c#"],
            "c#": ["c_sharp", "csharp"],
            "c++": ["cpp"],
            "cpp": ["c++"],
            "typescript": ["tsx", "ts"],
            "javascript": ["jsx", "js"],
            "python": ["py"],
            "ruby": ["rb"],
            "golang": ["go"],
            "rust": ["rs"],
            "shell": ["bash", "sh"],
            "bash": ["shell", "sh"],
            "yaml": ["yml"],
        }

        # Try all variants of this language
        all_langs_to_try = [lang] + lang_variants.get(lang, [])

        for current_lang in all_langs_to_try:
            try:
                language = get_language(current_lang)
                parser = get_parser(current_lang)
                if self.verbose:
                    self.io.tool_output(f"Found parser for {current_lang}")
                # If we found a working parser, set lang to current_lang and exit the loop
                lang = current_lang
                break
            except Exception as err:
                if self.verbose:
                    self.io.tool_warning(f"Error getting parser for {current_lang}: {err}")
        else:
            # If we've tried all variants and still can't find a parser, return
            if self.verbose:
                self.io.tool_warning(f"No parser found for {fname} after trying variants")
            return

        # Get query file for the language
        query_scm_path = get_scm_fname(lang)
        if not query_scm_path or not os.path.exists(query_scm_path):
            if self.verbose:
                self.io.tool_warning(f"No query file found for language: {lang}")
            return

        if self.verbose:
            self.io.tool_output(f"Using query file: {query_scm_path}")

        try:
            query_scm = query_scm_path.read_text()
            if self.verbose:
                self.io.tool_output(f"Read query file ({len(query_scm)} bytes)")
        except Exception as err:
            if self.verbose:
                self.io.tool_warning(f"Error reading query file for {lang}: {err}")
            return

        # Read the file content
        code = self.io.read_text(fname)
        if not code:
            if self.verbose:
                self.io.tool_warning(f"Could not read file content: {fname}")
            return

        if self.verbose:
            self.io.tool_output(f"Read file content ({len(code)} bytes)")

        # Parse the source code
        try:
            tree = parser.parse(bytes(code, "utf-8"))
            if self.verbose:
                self.io.tool_output("Parsed file successfully")
        except Exception as err:
            if self.verbose:
                self.io.tool_warning(f"Error parsing {fname}: {err}")
            return

        # Run the tags queries
        try:
            query = language.query(query_scm)

            # Handle different tree-sitter versions
            if USING_TSL_PACK:
                try:
                    captures = query.captures(tree.root_node)
                except AttributeError:
                    # For newer tree-sitter, try using capture_matches
                    matches = query.matches(tree.root_node)
                    captures = []
                    for match in matches:
                        for capture in match.captures:
                            captures.append((capture.node, capture.name))
            else:
                captures = query.captures(tree.root_node)

            if self.verbose:
                capture_count = len(captures) if isinstance(captures, list) else sum(len(nodes) for _, nodes in captures.items())
                self.io.tool_output(f"Successfully queried {fname} with {capture_count} captures")
        except Exception as err:
            if self.verbose:
                self.io.tool_warning(f"Error querying {fname}: {err}")
                self.io.tool_warning(f"Full error: {repr(err)}")
            return

        saw = set()
        all_nodes = []

        # Process captures based on tree-sitter version
        if USING_TSL_PACK:
            if isinstance(captures, dict):
                # Dictionary format with tag -> [nodes]
                for tag, nodes in captures.items():
                    all_nodes += [(node, tag) for node in nodes]
            else:
                # List format with (node, tag) tuples
                all_nodes = captures
        else:
            all_nodes = list(captures)

        # Extract symbols from captures
        definition_count = 0
        for node, tag in all_nodes:
            if tag.startswith("name.definition."):
                kind = "def"
                definition_count += 1
            elif tag.startswith("name.reference."):
                kind = "ref"
            else:
                continue

            saw.add(kind)

            # Get node text safely
            try:
                node_text = node.text.decode("utf-8")
            except (AttributeError, UnicodeDecodeError):
                if hasattr(node, 'text'):
                    try:
                        node_text = str(node.text)
                    except (ValueError, TypeError):
                        continue
                else:
                    continue

            # Create and yield the tag
            result = Tag(
                rel_fname=rel_fname,
                fname=fname,
                name=node_text,
                kind=kind,
                line=node.start_point[0],
            )

            yield result

        if self.verbose and definition_count > 0:
            self.io.tool_output(f"Found {definition_count} symbol definitions in {fname}")

        # If we have both definitions and references, no need for fallback
        if "ref" in saw:
            return
        if "def" not in saw:
            return

        # We saw defs, without any refs
        # Some tags files only provide defs (cpp, for example)
        # Use pygments to backfill refs
        if self.verbose:
            self.io.tool_output(f"Using Pygments fallback for references in {fname}")

        try:
            lexer = guess_lexer_for_filename(fname, code)
        except Exception:  # On Windows, bad ref to time.clock which is deprecated?
            if self.verbose:
                self.io.tool_warning(f"Error getting lexer for {fname}")
            return

        try:
            tokens = list(lexer.get_tokens(code))
            tokens = [token[1] for token in tokens if token[0] in Token.Name]

            for token in tokens:
                yield Tag(
                    rel_fname=rel_fname,
                    fname=fname,
                    name=token,
                    kind="ref",
                    line=-1,
                )

            if self.verbose:
                self.io.tool_output(f"Added {len(tokens)} reference tokens from Pygments for {fname}")
        except Exception as err:
            if self.verbose:
                self.io.tool_warning(f"Error getting tokens from Pygments: {err}")

    def get_ranked_tags(
        self, chat_fnames, other_fnames, mentioned_fnames, mentioned_idents, progress=None
    ):
        import networkx as nx

        defines = defaultdict(set)
        references = defaultdict(list)
        definitions = defaultdict(set)

        personalization = dict()

        fnames = set(chat_fnames).union(set(other_fnames))
        chat_rel_fnames = set()

        fnames = sorted(fnames)

        # Default personalization for unspecified files is 1/num_nodes
        # https://networkx.org/documentation/stable/_modules/networkx/algorithms/link_analysis/pagerank_alg.html#pagerank
        if fnames:
            personalize = 100 / len(fnames)
        else:
            personalize = 0.0

        try:
            cache_size = len(self.TAGS_CACHE)
        except SQLITE_ERRORS as e:
            self.tags_cache_error(e)
            cache_size = len(self.TAGS_CACHE)

        if len(fnames) - cache_size > 100:
            self.io.tool_output(
                "Initial repo scan can be slow in larger repos, but only happens once."
            )
            fnames = tqdm(fnames, desc="Scanning repo")
            showing_bar = True
        else:
            showing_bar = False

        for fname in fnames:
            if self.verbose:
                self.io.tool_output(f"Processing {fname}")
            if progress and not showing_bar:
                progress()

            try:
                file_ok = Path(fname).is_file()
            except OSError:
                file_ok = False

            if not file_ok:
                if fname not in self.warned_files:
                    self.io.tool_warning(f"Repo-map can't include {fname}")
                    self.io.tool_output(
                        "Has it been deleted from the file system but not from git?"
                    )
                    self.warned_files.add(fname)
                continue

            # dump(fname)
            rel_fname = self.get_rel_fname(fname)

            if fname in chat_fnames:
                personalization[rel_fname] = personalize
                chat_rel_fnames.add(rel_fname)

            if rel_fname in mentioned_fnames:
                personalization[rel_fname] = personalize

            tags = list(self.get_tags(fname, rel_fname))
            if tags is None:
                continue

            for tag in tags:
                if tag.kind == "def":
                    defines[tag.name].add(rel_fname)
                    key = (rel_fname, tag.name)
                    definitions[key].add(tag)

                elif tag.kind == "ref":
                    references[tag.name].append(rel_fname)

        ##
        # dump(defines)
        # dump(references)
        # dump(personalization)

        if not references:
            references = dict((k, list(v)) for k, v in defines.items())

        idents = set(defines.keys()).intersection(set(references.keys()))

        G = nx.MultiDiGraph()

        # Add a small self-edge for every definition that has no references
        # Helps with tree-sitter 0.23.2 with ruby, where "def greet(name)"
        # isn't counted as a def AND a ref. tree-sitter 0.24.0 does.
        for ident in defines.keys():
            if ident in references:
                continue
            for definer in defines[ident]:
                G.add_edge(definer, definer, weight=0.1, ident=ident)

        for ident in idents:
            if progress:
                progress()

            definers = defines[ident]
            if ident in mentioned_idents:
                mul = 10
            elif ident.startswith("_"):
                mul = 0.1
            else:
                mul = 1

            for referencer, num_refs in Counter(references[ident]).items():
                for definer in definers:
                    # dump(referencer, definer, num_refs, mul)
                    # if referencer == definer:
                    #    continue

                    # scale down so high freq (low value) mentions don't dominate
                    num_refs = math.sqrt(num_refs)

                    G.add_edge(referencer, definer, weight=mul * num_refs, ident=ident)

        if not references:
            pass

        if personalization:
            pers_args = dict(personalization=personalization, dangling=personalization)
        else:
            pers_args = dict()

        try:
            ranked = nx.pagerank(G, weight="weight", **pers_args)
        except ZeroDivisionError:
            # Issue #1536
            try:
                ranked = nx.pagerank(G, weight="weight")
            except ZeroDivisionError:
                return []

        # distribute the rank from each source node, across all of its out edges
        ranked_definitions = defaultdict(float)
        for src in G.nodes:
            if progress:
                progress()

            src_rank = ranked[src]
            total_weight = sum(data["weight"] for _src, _dst, data in G.out_edges(src, data=True))
            # dump(src, src_rank, total_weight)
            for _src, dst, data in G.out_edges(src, data=True):
                data["rank"] = src_rank * data["weight"] / total_weight
                ident = data["ident"]
                ranked_definitions[(dst, ident)] += data["rank"]

        ranked_tags = []
        ranked_definitions = sorted(
            ranked_definitions.items(), reverse=True, key=lambda x: (x[1], x[0])
        )

        # dump(ranked_definitions)

        for (fname, ident), rank in ranked_definitions:
            # print(f"{rank:.03f} {fname} {ident}")
            if fname in chat_rel_fnames:
                continue
            ranked_tags += list(definitions.get((fname, ident), []))

        rel_other_fnames_without_tags = set(self.get_rel_fname(fname) for fname in other_fnames)

        fnames_already_included = set(rt[0] for rt in ranked_tags)

        top_rank = sorted([(rank, node) for (node, rank) in ranked.items()], reverse=True)
        for rank, fname in top_rank:
            if fname in rel_other_fnames_without_tags:
                rel_other_fnames_without_tags.remove(fname)
            if fname not in fnames_already_included:
                ranked_tags.append((fname,))

        for fname in rel_other_fnames_without_tags:
            ranked_tags.append((fname,))

        return ranked_tags

    def get_ranked_tags_map(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
        force_refresh=False,
    ):
        """
        Get a ranked tags map, with caching for efficiency.

        For very large repositories, this method tries to use caching when appropriate
        to avoid reprocessing the entire repository every time.
        """
        # Create a cache key
        # For large repositories, only use the count for cache keys to save memory
        if other_fnames and len(other_fnames) > 1000:
            # Just include the count rather than all entries to keep the key small
            other_fnames_key = len(other_fnames)
        else:
            other_fnames_key = tuple(sorted(other_fnames)) if other_fnames else None

        if chat_fnames and len(chat_fnames) > 1000:
            chat_fnames_key = len(chat_fnames)
        else:
            chat_fnames_key = tuple(sorted(chat_fnames)) if chat_fnames else None

        cache_key = [
            chat_fnames_key,
            other_fnames_key,
            max_map_tokens,
        ]

        if self.refresh == "auto":
            if mentioned_fnames and len(mentioned_fnames) > 1000:
                mentioned_fnames_key = len(mentioned_fnames)
            else:
                mentioned_fnames_key = tuple(sorted(mentioned_fnames)) if mentioned_fnames else None

            if mentioned_idents and len(mentioned_idents) > 1000:
                mentioned_idents_key = len(mentioned_idents)
            else:
                mentioned_idents_key = tuple(sorted(mentioned_idents)) if mentioned_idents else None

            cache_key += [
                mentioned_fnames_key,
                mentioned_idents_key,
            ]

        try:
            cache_key = tuple(cache_key)
        except TypeError:
            # If we can't make a tuple (e.g., due to unhashable types),
            # just use a unique identifier based on length
            key_str = f"{len(chat_fnames or [])}-{len(other_fnames or [])}-{max_map_tokens}"
            cache_key = hash(key_str)

        # When force_refresh is True, don't use cache and remove any cached entry
        if force_refresh and cache_key in self.map_cache:
            if self.verbose:
                chat_count = len(chat_fnames) if isinstance(chat_fnames, list) else "?"
                other_count = len(other_fnames) if isinstance(other_fnames, list) else "?"
                self.io.tool_output(f"Force refreshing map cache for {chat_count} chat files and {other_count} other files")
            del self.map_cache[cache_key]

        use_cache = False
        if not force_refresh:
            if self.refresh == "manual" and self.last_map:
                return self.last_map

            if self.refresh == "always":
                use_cache = False
            elif self.refresh == "files":
                use_cache = True
            elif self.refresh == "auto":
                use_cache = self.map_processing_time > 1.0

            # Check if the result is in the cache
            if use_cache and cache_key in self.map_cache:
                if self.verbose:
                    chat_count = len(chat_fnames) if isinstance(chat_fnames, list) else "?"
                    other_count = len(other_fnames) if isinstance(other_fnames, list) else "?"
                    self.io.tool_output(f"Using cached map for {chat_count} chat files and {other_count} other files")
                return self.map_cache[cache_key]

        # Check if we need to process file modifications in refresh "files" mode
        # For large repositories, only check a sample of files to detect changes
        process_modifications = False
        if self.refresh == "files" and other_fnames:
            # For very large repos, check at most 100 random files
            sample_size = min(100, len(other_fnames))
            if len(other_fnames) > sample_size:
                import random
                sample_fnames = random.sample(other_fnames, sample_size)
            else:
                sample_fnames = other_fnames

            for fname in sample_fnames:
                file_mtime = self.get_mtime(fname)
                cache_key_file = fname
                if cache_key_file in self.TAGS_CACHE:
                    try:
                        if self.TAGS_CACHE[cache_key_file].get("mtime") != file_mtime:
                            if self.verbose:
                                rel_fname = self.get_rel_fname(fname)
                                self.io.tool_output(f"File modified: {rel_fname}")
                            process_modifications = True
                            break
                    except SQLITE_ERRORS:
                        process_modifications = True
                        break

        # If files have been modified in "files" mode, force regeneration
        if process_modifications:
            force_refresh = True
            if self.verbose:
                self.io.tool_output("Detected file modifications, refreshing map")

        # If not in cache or force_refresh is True, generate the map
        start_time = time.time()
        result = self.get_ranked_tags_map_uncached(
            chat_fnames, other_fnames, max_map_tokens, mentioned_fnames, mentioned_idents, force_refresh
        )
        end_time = time.time()
        self.map_processing_time = end_time - start_time

        # Store the result in the cache
        self.map_cache[cache_key] = result
        self.last_map = result

        return result

    def get_ranked_tags_map_uncached(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
        force_refresh=False,
    ):
        """
        Generate a comprehensive repository map, potentially split across multiple files.

        If max_map_tokens is specified, the map will be split into multiple files,
        each containing no more than max_map_tokens tokens. This ensures that no symbol
        or section is truncated in the middle.
        """
        if not other_fnames:
            other_fnames = list()
        if not max_map_tokens:
            max_map_tokens = self.max_map_tokens
        if not mentioned_fnames:
            mentioned_fnames = set()
        if not mentioned_idents:
            mentioned_idents = set()

        if self.verbose:
            self.io.tool_output(f"Getting ranked tags map with {len(chat_fnames)} chat files and {len(other_fnames)} other files")
            self.io.tool_output(f"Max tokens per part: {max_map_tokens}")
            if force_refresh:
                self.io.tool_output("Force refresh: True")

        # Expand directory entries to individual files
        expanded_chat_fnames = []
        for fname in chat_fnames:
            if os.path.isdir(fname):
                expanded_chat_fnames.extend(find_src_files(fname))
            else:
                expanded_chat_fnames.append(fname)

        expanded_other_fnames = []
        for fname in other_fnames:
            if os.path.isdir(fname):
                expanded_other_fnames.extend(find_src_files(fname))
            else:
                expanded_other_fnames.append(fname)

        chat_fnames = expanded_chat_fnames
        other_fnames = expanded_other_fnames

        if self.verbose:
            self.io.tool_output(f"After directory expansion: {len(chat_fnames)} chat files and {len(other_fnames)} other files")

        spin = Spinner("Updating repo map")

        # Clear cache if forcing refresh
        if force_refresh:
            if self.verbose:
                self.io.tool_output("Clearing tag cache due to force refresh")
            # Reset the cache for the specified files
            for fname in chat_fnames + other_fnames:
                cache_key = fname
                if cache_key in self.TAGS_CACHE:
                    try:
                        del self.TAGS_CACHE[cache_key]
                    except SQLITE_ERRORS:
                        pass

        # Process all files
        all_fnames = chat_fnames + other_fnames

        # Group by extension
        files_by_ext = {}
        for fname in all_fnames:
            rel_fname = self.get_rel_fname(fname)
            ext = os.path.splitext(rel_fname)[1].lower() or "no_extension"
            if ext not in files_by_ext:
                files_by_ext[ext] = []
            files_by_ext[ext].append((fname, rel_fname))

        # Define language-specific extraction patterns
        language_patterns = {
            '.py': [
                # Python patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*def\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*async\s+def\s+(\w+)', 'kind': 'async_function', 'context_lines': 4},
                # Nested class and method definitions (indented)
                {'regex': r'^\s+class\s+(\w+)', 'kind': 'nested_class', 'context_lines': 6},
                {'regex': r'^\s+def\s+(\w+)', 'kind': 'method', 'context_lines': 4},
                {'regex': r'^\s+async\s+def\s+(\w+)', 'kind': 'async_method', 'context_lines': 4},
            ],
            '.js': [
                # JavaScript patterns
                {'regex': r'^\s*function\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*const\s+(\w+)\s*=\s*function', 'kind': 'const_function', 'context_lines': 4},
                {'regex': r'^\s*const\s+(\w+)\s*=\s*\(.*\)\s*=>', 'kind': 'arrow_function', 'context_lines': 4},
                {'regex': r'^\s*let\s+(\w+)\s*=\s*function', 'kind': 'let_function', 'context_lines': 4},
                {'regex': r'^\s*var\s+(\w+)\s*=\s*function', 'kind': 'var_function', 'context_lines': 4},
            ],
            '.ts': [
                # TypeScript patterns
                {'regex': r'^\s*function\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*interface\s+(\w+)', 'kind': 'interface', 'context_lines': 6},
                {'regex': r'^\s*type\s+(\w+)', 'kind': 'type', 'context_lines': 4},
                {'regex': r'^\s*const\s+(\w+)\s*[:=]', 'kind': 'const', 'context_lines': 3},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 5},
            ],
            '.tsx': [
                # TSX patterns (React+TypeScript)
                {'regex': r'^\s*function\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*const\s+(\w+)\s*=\s*\(.*\)\s*=>', 'kind': 'component', 'context_lines': 6},
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*interface\s+(\w+)', 'kind': 'interface', 'context_lines': 5},
                {'regex': r'^\s*type\s+(\w+)', 'kind': 'type', 'context_lines': 4},
            ],
            '.java': [
                # Java patterns
                {'regex': r'^\s*public\s+class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*interface\s+(\w+)', 'kind': 'interface', 'context_lines': 5},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 5},
                {'regex': r'^\s*(public|private|protected).*\s+(\w+)\s*\(', 'kind': 'method', 'context_lines': 4},
            ],
            '.cpp': [
                # C++ patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*struct\s+(\w+)', 'kind': 'struct', 'context_lines': 6},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 4},
                {'regex': r'^\s*.*\s+(\w+)\s*\([^)]*\)\s*(?:\{|$)', 'kind': 'function', 'context_lines': 4},
            ],
            '.c': [
                # C patterns
                {'regex': r'^\s*struct\s+(\w+)', 'kind': 'struct', 'context_lines': 6},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 4},
                {'regex': r'^\s*.*\s+(\w+)\s*\([^)]*\)\s*(?:\{|$)', 'kind': 'function', 'context_lines': 4},
            ],
            '.rb': [
                # Ruby patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*module\s+(\w+)', 'kind': 'module', 'context_lines': 5},
                {'regex': r'^\s*def\s+(\w+)', 'kind': 'method', 'context_lines': 4},
            ],
            '.go': [
                # Go patterns
                {'regex': r'^\s*func\s+(\w+)', 'kind': 'function', 'context_lines': 5},
                {'regex': r'^\s*type\s+(\w+)\s+struct', 'kind': 'struct', 'context_lines': 6},
                {'regex': r'^\s*type\s+(\w+)\s+interface', 'kind': 'interface', 'context_lines': 6},
            ],
            '.rs': [
                # Rust patterns
                {'regex': r'^\s*fn\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*struct\s+(\w+)', 'kind': 'struct', 'context_lines': 5},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 5},
                {'regex': r'^\s*trait\s+(\w+)', 'kind': 'trait', 'context_lines': 5},
                {'regex': r'^\s*impl.*\s+(\w+)', 'kind': 'impl', 'context_lines': 6},
            ],
            '.php': [
                # PHP patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*function\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*interface\s+(\w+)', 'kind': 'interface', 'context_lines': 5},
            ],
            '.kt': [
                # Kotlin patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*fun\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*interface\s+(\w+)', 'kind': 'interface', 'context_lines': 5},
                {'regex': r'^\s*data\s+class\s+(\w+)', 'kind': 'data_class', 'context_lines': 4},
            ],
            '.swift': [
                # Swift patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*struct\s+(\w+)', 'kind': 'struct', 'context_lines': 5},
                {'regex': r'^\s*func\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 5},
                {'regex': r'^\s*protocol\s+(\w+)', 'kind': 'protocol', 'context_lines': 5},
            ],
            '.cs': [
                # C# patterns
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
                {'regex': r'^\s*interface\s+(\w+)', 'kind': 'interface', 'context_lines': 5},
                {'regex': r'^\s*(public|private|protected|internal).*\s+(\w+)\s*\(', 'kind': 'method', 'context_lines': 4},
                {'regex': r'^\s*enum\s+(\w+)', 'kind': 'enum', 'context_lines': 4},
                {'regex': r'^\s*struct\s+(\w+)', 'kind': 'struct', 'context_lines': 5},
            ],
            '.sol': [
                # Solidity patterns
                {'regex': r'^\s*contract\s+(\w+)', 'kind': 'contract', 'context_lines': 6},
                {'regex': r'^\s*function\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*struct\s+(\w+)', 'kind': 'struct', 'context_lines': 5},
                {'regex': r'^\s*event\s+(\w+)', 'kind': 'event', 'context_lines': 3},
            ],
            '.ex': [
                # Elixir patterns
                {'regex': r'^\s*defmodule\s+(\w+)', 'kind': 'module', 'context_lines': 5},
                {'regex': r'^\s*def\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*defp\s+(\w+)', 'kind': 'private_function', 'context_lines': 4},
            ],
            '.ml': [
                # OCaml patterns
                {'regex': r'^\s*let\s+(\w+)', 'kind': 'binding', 'context_lines': 4},
                {'regex': r'^\s*type\s+(\w+)', 'kind': 'type', 'context_lines': 5},
                {'regex': r'^\s*class\s+(\w+)', 'kind': 'class', 'context_lines': 6},
            ],
            '.r': [
                # R patterns
                {'regex': r'^\s*(\w+)\s*<-\s*function', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*(\w+)\s*=\s*function', 'kind': 'function', 'context_lines': 4},
            ],
            '.lua': [
                # Lua patterns
                {'regex': r'^\s*function\s+(\w+)', 'kind': 'function', 'context_lines': 4},
                {'regex': r'^\s*local\s+function\s+(\w+)', 'kind': 'local_function', 'context_lines': 4},
                {'regex': r'^\s*(\w+)\s*=\s*function', 'kind': 'function_var', 'context_lines': 4},
            ]
        }

        # Create file list sections grouped by extension
        extension_sections = []
        for ext, files in sorted(files_by_ext.items()):
            # Prepare file lists without processing full content yet
            file_list = "\n".join(f"  {rel_fname}" for _, rel_fname in sorted(files, key=lambda x: x[1]))

            if file_list:
                if ext == "no_extension":
                    ext_header = "Files without extension:"
                else:
                    ext_header = f"{ext} files:"

                extension_sections.append((ext, f"{ext_header}\n{file_list}\n\n"))

        # If max_map_tokens is 0 or negative, don't split into parts
        if max_map_tokens <= 0:
            # Create a single unified map with just file listings
            result = "Repository contents:\n\n"
            # Add all extension sections
            for ext, section in extension_sections:
                result += section

            spin.end()
            return result

        # Get repository name for naming output files
        repo_name = os.path.basename(os.path.normpath(self.root))
        if not repo_name or repo_name == '.':
            repo_name = 'repo'

        # Create multiple map parts, each staying under the token limit
        current_part = 1
        output_parts = []

        # Start with the header and extension sections for the first part
        current_map = "Repository contents:\n\n"

        # Add all extension sections to the first part
        for ext, section in extension_sections:
            # Check if adding this section would exceed the token limit
            section_tokens = self.token_count(section)
            current_tokens = self.token_count(current_map)

            if current_tokens + section_tokens <= max_map_tokens:
                # Add the section to the current map
                current_map += section
            else:
                # Save the current map as a part and start a new one
                output_parts.append((current_part, current_map))
                current_part += 1
                current_map = f"Repository contents (continued, part {current_part}):\n\n"
                current_map += section

        # Now process files by extension to extract symbols
        # We'll do this one extension at a time to minimize memory usage
        for ext, patterns in language_patterns.items():
            if ext in files_by_ext:
                files_for_processing = files_by_ext[ext]

                if self.verbose:
                    self.io.tool_output(f"Processing {len(files_for_processing)} {ext} files")

                # Process files one by one, adding to the current part
                for abs_fname, rel_fname in files_for_processing:
                    # Skip already processed files
                    if current_map.find(f"\n{rel_fname}:\n") >= 0:
                        continue

                    # Read file content
                    content = self.io.read_text(abs_fname)
                    if not content:
                        continue

                    lines = content.splitlines()
                    if not lines:
                        continue

                    # Track symbols found in this file
                    symbols_found = []

                    # Apply each regex pattern
                    for pattern in patterns:
                        regex = re.compile(pattern['regex'])
                        context_lines = pattern['context_lines']

                        for i, line in enumerate(lines):
                            match = regex.search(line)
                            if match:
                                symbol_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                                symbols_found.append((i, line, symbol_name, context_lines))

                    # If symbols were found, add them to output
                    if symbols_found:
                        file_output = [f"\n{rel_fname}:\n"]

                        # Sort symbols by line number
                        symbols_found.sort(key=lambda x: x[0])

                        # Track the last line we added to avoid duplication
                        last_line_added = -5  # Ensure we don't skip the first symbol

                        for line_num, line, symbol, context in symbols_found:
                            # Skip if too close to previous symbol
                            if line_num <= last_line_added + 2:
                                continue

                            last_line_added = line_num

                            # Add the symbol with context
                            file_output.append("⋮")
                            file_output.append(f"│{line.rstrip()}")

                            # Add context lines
                            context_count = 0
                            for j in range(line_num + 1, min(line_num + context + 1, len(lines))):
                                context_line = lines[j].rstrip()
                                # For functions/methods, stop at first empty line
                                if not context_line and pattern['kind'] != 'class':
                                    break
                                file_output.append(f"│{context_line}")
                                context_count += 1
                                if context_count >= context:
                                    break

                        file_output.append("⋮")
                        file_content = "\n".join(file_output)

                        # Check if adding this section would exceed the token limit
                        section_tokens = self.token_count(file_content)
                        current_tokens = self.token_count(current_map)

                        # If this section alone is larger than max_map_tokens, we need to warn
                        if section_tokens > max_map_tokens:
                            if self.verbose:
                                self.io.tool_warning(f"Section for file {rel_fname} exceeds token limit ({section_tokens} > {max_map_tokens})")
                                self.io.tool_warning("This section will be placed in its own part, but may still be truncated by models")

                        # Check if we need to start a new part
                        if current_tokens + section_tokens > max_map_tokens:
                            # Save the current map as a part
                            output_parts.append((current_part, current_map))
                            current_part += 1
                            current_map = f"Repository contents (continued, part {current_part}):\n\n"

                        # Add the section to the current map
                        current_map += file_content

                        # If after adding, we're already at the limit, start a new part
                        if self.token_count(current_map) >= max_map_tokens * 0.9:  # 90% utilization threshold
                            output_parts.append((current_part, current_map))
                            current_part += 1
                            current_map = f"Repository contents (continued, part {current_part}):\n\n"

                    # Clear the file content from memory to reduce memory usage
                    content = None
                    lines = None

                # Help Python's garbage collector by explicitly clearing variables
                files_for_processing = None

        # Add the final part if it's not empty
        if current_map.strip() != f"Repository contents (continued, part {current_part}):" and len(current_map) > 40:
            output_parts.append((current_part, current_map))

        # Write parts to disk one at a time
        for part_number, content in output_parts:
            part_tokens = self.token_count(content)
            part_filename = f"repomap_{repo_name}_part{part_number:05d}.txt"
            part_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", part_filename)

            # Ensure the output directory exists
            os.makedirs(os.path.dirname(part_path), exist_ok=True)

            # Write the file
            with open(part_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if self.verbose:
                self.io.tool_output(f"Wrote part {part_number} with {part_tokens:.1f} tokens to {part_filename}")

            # Clear content from memory after writing to disk
            content = None

        if self.verbose:
            self.io.tool_output(f"Repository map split into {len(output_parts)} parts")

        # Return only the first part as the result
        # The calling function will need to handle accessing other parts if needed
        spin.end()

        # Check if we have any parts
        if not output_parts:
            return "Repository contents:\n\n"

        # Get the first part from disk to avoid keeping it in memory
        first_part_filename = f"repomap_{repo_name}_part00001.txt"
        first_part_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", first_part_filename)

        try:
            with open(first_part_path, 'r', encoding='utf-8') as f:
                first_part_content = f.read()
            return first_part_content
        except Exception as e:
            if self.verbose:
                self.io.tool_warning(f"Error reading first part from disk: {e}")
            # In case of error, return a minimal content
            return "Repository contents:\n\n"

        # Initialize ranked_tags
        ranked_tags = self.get_ranked_tags(all_fnames, chat_fnames)
        
        # If we have no tags, create a basic output with file listings
        if not ranked_tags and chat_fnames:
            if self.verbose:
                self.io.tool_output("No tags found, creating basic file listing")
            result = "Repository contents:\n\n"

            # Group files by extension for better organization
            files_by_ext = {}
            for fname in sorted(chat_fnames):
                rel_fname = self.get_rel_fname(fname)
                ext = os.path.splitext(rel_fname)[1].lower() or "no_extension"
                if ext not in files_by_ext:
                    files_by_ext[ext] = []
                files_by_ext[ext].append(rel_fname)

            # Print each extension group
            for ext, files in sorted(files_by_ext.items()):
                if ext == "no_extension":
                    result += "Files without extension:\n"
                else:
                    result += f"{ext} files:\n"

                for f in sorted(files):
                    result += f"  {f}\n"
                result += "\n"

            return result

        # Use all ranked tags - skip binary search for now to debug symbol extraction
        chat_rel_fnames = set(self.get_rel_fname(fname) for fname in chat_fnames)

        # Get a simple file listing first in case tree generation fails
        fallback_result = "Repository contents:\n\n"

        # Group files by extension for better organization
        files_by_ext = {}
        for fname in sorted(all_fnames):
            rel_fname = self.get_rel_fname(fname)
            ext = os.path.splitext(rel_fname)[1].lower() or "no_extension"
            if ext not in files_by_ext:
                files_by_ext[ext] = []
            files_by_ext[ext].append(rel_fname)

        # Format the file listing
        for ext, files in sorted(files_by_ext.items()):
            if ext == "no_extension":
                fallback_result += "Files without extension:\n"
            else:
                fallback_result += f"{ext} files:\n"

            for f in sorted(files):
                fallback_result += f"  {f}\n"
            fallback_result += "\n"

        # Generate the tree with symbols
        try:
            tree = self.to_tree(ranked_tags, chat_rel_fnames)
            num_tokens = self.token_count(tree)

            if self.verbose:
                self.io.tool_output(f"Generated tree with {len(ranked_tags)} tags: {num_tokens} tokens")

            # Check if tree exceeds token limit
            if num_tokens > max_map_tokens and max_map_tokens > 0:
                if self.verbose:
                    self.io.tool_output(f"Tree exceeds token limit ({num_tokens} > {max_map_tokens}), truncating")

                # Simple truncation strategy - reduce the number of tags
                truncation_factor = max_map_tokens / num_tokens
                num_tags_to_keep = max(1, int(len(ranked_tags) * truncation_factor))

                if self.verbose:
                    self.io.tool_output(f"Keeping {num_tags_to_keep} tags out of {len(ranked_tags)}")

                # Regenerate tree with fewer tags
                tree = self.to_tree(ranked_tags[:num_tags_to_keep], chat_rel_fnames)

            # Ensure the tree is not empty
            if not tree or tree.strip() == "":
                if self.verbose:
                    self.io.tool_output("Generated tree is empty, using fallback listing")
                tree = fallback_result
        except Exception as e:
            if self.verbose:
                self.io.tool_warning(f"Error generating tree: {str(e)}")
            tree = fallback_result

        spin.end()

        if tree and tree.strip():
            return tree
        elif chat_fnames:
            # If no tree was generated but we have files, create a basic output
            if self.verbose:
                self.io.tool_output("No tree generated, creating basic file listing")
            result = "Repository contents:\n\n"

            # Group files by extension for better organization
            files_by_ext = {}
            for fname in sorted(chat_fnames):
                rel_fname = self.get_rel_fname(fname)
                ext = os.path.splitext(rel_fname)[1].lower() or "no_extension"
                if ext not in files_by_ext:
                    files_by_ext[ext] = []
                files_by_ext[ext].append(rel_fname)

            # Print each extension group
            for ext, files in sorted(files_by_ext.items()):
                if ext == "no_extension":
                    result += "Files without extension:\n"
                else:
                    result += f"{ext} files:\n"

                for f in sorted(files):
                    result += f"  {f}\n"
                result += "\n"

            return result
        else:
            return None

    tree_cache = dict()

    def render_tree(self, abs_fname, rel_fname, lois):
        mtime = self.get_mtime(abs_fname)
        key = (rel_fname, tuple(sorted(lois)), mtime)

        if key in self.tree_cache:
            return self.tree_cache[key]

        if (
            rel_fname not in self.tree_context_cache
            or self.tree_context_cache[rel_fname]["mtime"] != mtime
        ):
            code = self.io.read_text(abs_fname) or ""
            if not code.endswith("\n"):
                code += "\n"

            context = TreeContext(
                rel_fname,
                code,
                color=False,
                line_number=False,
                child_context=False,
                last_line=False,
                margin=0,
                mark_lois=False,
                loi_pad=0,
                # header_max=30,
                show_top_of_file_parent_scope=False,
            )
            self.tree_context_cache[rel_fname] = {"context": context, "mtime": mtime}

        context = self.tree_context_cache[rel_fname]["context"]
        context.lines_of_interest = set()
        context.add_lines_of_interest(lois)
        context.add_context()
        res = context.format()
        self.tree_cache[key] = res
        return res

    def generate_symbol_map(self, abs_fname, rel_fname, tags):
        """Generate a map of symbols defined in a file with their context."""
        if not tags:
            return ""

        # Get the file content
        code = self.io.read_text(abs_fname) or ""
        if not code:
            return ""

        lines = code.splitlines()
        if not lines:
            return ""

        # Group tags by lines to avoid duplicate lines
        line_to_tags = {}
        for tag in tags:
            if tag.line >= 0:  # Only include tags with valid line numbers
                if tag.line not in line_to_tags:
                    line_to_tags[tag.line] = []
                line_to_tags[tag.line].append(tag)

        # Sort the lines
        sorted_lines = sorted(line_to_tags.keys())

        if self.verbose:
            self.io.tool_output(f"Processing {len(sorted_lines)} symbol lines in {rel_fname}")

        output = []
        last_line_added = -1

        for line_num in sorted_lines:
            # Skip if it's too close to the previous line we added
            if 0 <= last_line_added < line_num <= last_line_added + 2:
                continue

            # Get the symbol name(s) from this line
            symbols = [tag.name for tag in line_to_tags[line_num]]
            if not symbols:
                continue

            if self.verbose:
                self.io.tool_output(f"  Found symbol(s) at line {line_num}: {', '.join(symbols)}")

            # Check if this is a class, function, or method definition
            current_line = lines[line_num] if line_num < len(lines) else ""
            is_class = "class " in current_line
            is_function = "def " in current_line or "function " in current_line
            is_method = bool(re.search(r'^\s+def\s+', current_line))

            # Determine context to capture
            context_before = 0  # Lines before the definition
            context_after = 0   # Lines after the definition

            if is_class:
                # For classes, capture the class definition and a few methods
                context_before = 0
                context_after = 5
            elif is_function or is_method:
                # For functions/methods, capture the signature and a few lines of body
                context_before = 0
                context_after = 3
            else:
                # For other symbols, just show the line and 2 lines after
                context_before = 0
                context_after = 2

            # Calculate line range to show
            start_line = max(0, line_num - context_before)
            end_line = min(len(lines) - 1, line_num + context_after)

            # Gather the definition context
            definition_context = []
            definition_found = False

            for i in range(start_line, end_line + 1):
                if i >= len(lines):
                    break

                line = lines[i]

                # Mark when we reach the actual symbol definition
                if i == line_num:
                    definition_found = True

                # Clean up the line (remove trailing whitespace)
                cleaned_line = line.rstrip()

                # Add the line with the symbol marker
                definition_context.append(f"│{cleaned_line}")

                # If we find a blank line after the definition and we're not in a class,
                # stop collecting context
                if definition_found and not is_class and not cleaned_line:
                    break

            # Add a horizontal ellipsis marker before and after definition blocks
            if definition_context:
                output.append("⋮")
                output.extend(definition_context)
                last_line_added = line_num + len(definition_context) - 1

        # Add a final ellipsis if there were any definitions
        if output:
            output.append("⋮")

        return "\n".join(output)

    def to_tree(self, tags, chat_rel_fnames):
        if not tags:
            return "Repository contents:\n\n"

        # Group tags by filename
        files_to_tags = {}
        for tag in tags:
            if type(tag) is not Tag:
                # This is just a filename tuple
                rel_fname = tag[0]
                if rel_fname in chat_rel_fnames:
                    continue
                if rel_fname not in files_to_tags:
                    files_to_tags[rel_fname] = []
            else:
                # This is a real tag
                rel_fname = tag.rel_fname
                if rel_fname in chat_rel_fnames:
                    continue
                if rel_fname not in files_to_tags:
                    files_to_tags[rel_fname] = []
                # Only include definition tags, not references
                if tag.kind == "def":
                    files_to_tags[rel_fname].append(tag)
                    if self.verbose:
                        self.io.tool_output(f"To Tree: Found symbol definition: {tag.name} in {rel_fname} at line {tag.line}")

        # Group files by extension
        files_by_extension = {}
        for rel_fname in files_to_tags.keys():
            ext = os.path.splitext(rel_fname)[1].lower() or "no_extension"
            if ext not in files_by_extension:
                files_by_extension[ext] = []
            files_by_extension[ext].append(rel_fname)

        all_outputs = []
        # Keep track of files that we've processed with symbols
        files_with_symbols = set()

        self.io.tool_output("DEBUG BEGIN: to_tree method")
        self.io.tool_output(f"DEBUG: Found {len(files_by_extension)} extension types: {list(files_by_extension.keys())}")

        # First, let's force-add all files with a direct implementation
        all_file_contents = {}

        # First, add files with symbols
        for ext, files in sorted(files_by_extension.items()):
            self.io.tool_output(f"DEBUG: Processing {len(files)} files with extension {ext}")
            for rel_fname in sorted(files):
                # Get the tags for this file
                file_tags = files_to_tags[rel_fname]

                self.io.tool_output(f"DEBUG: File {rel_fname} has {len(file_tags)} tags")

                # Find the absolute path to the file
                abs_fname = None
                for tag in file_tags:
                    if hasattr(tag, 'fname'):
                        abs_fname = tag.fname
                        break

                if not abs_fname:
                    # Try to reconstruct the abs_fname from rel_fname and root
                    abs_fname = os.path.join(self.root, rel_fname)

                self.io.tool_output(f"DEBUG: Absolute path for {rel_fname} is {abs_fname}")

                # Read the file content
                file_content = self.io.read_text(abs_fname) or ""
                if not file_content:
                    self.io.tool_warning(f"DEBUG: Could not read file content: {abs_fname}")
                    continue

                # Store the file content
                all_file_contents[rel_fname] = file_content

                # Get lines
                lines = file_content.splitlines()
                if not lines:
                    self.io.tool_warning(f"DEBUG: No lines in file: {abs_fname}")
                    continue

                # Process python files - add class and function definitions
                if ext == '.py':
                    files_with_symbols.add(rel_fname)
                    file_output = []
                    file_output.append("")
                    file_output.append(f"{rel_fname}:")

                    # Extract classes
                    class_defs = []
                    for i, line in enumerate(lines):
                        if line.strip().startswith('class '):
                            class_defs.append((i, line))

                    # Extract functions
                    func_defs = []
                    for i, line in enumerate(lines):
                        if line.strip().startswith('def '):
                            func_defs.append((i, line))

                    self.io.tool_output(f"DEBUG: Found {len(class_defs)} classes and {len(func_defs)} functions in {rel_fname}")

                    symbols_output = []

                    # Process classes
                    for line_num, line in class_defs:
                        symbols_output.append("⋮")
                        symbols_output.append(f"│{line.rstrip()}")

                        # Add class body
                        for i in range(line_num + 1, min(line_num + 6, len(lines))):
                            symbols_output.append(f"│{lines[i].rstrip()}")

                    # Process functions
                    for line_num, line in func_defs:
                        symbols_output.append("⋮")
                        symbols_output.append(f"│{line.rstrip()}")

                        # Add function body
                        for i in range(line_num + 1, min(line_num + 4, len(lines))):
                            context_line = lines[i].rstrip()
                            if not context_line:  # Stop at first empty line
                                break
                            symbols_output.append(f"│{context_line}")

                    if symbols_output:
                        symbols_output.append("⋮")
                        file_output.extend(symbols_output)
                        all_outputs.extend(file_output)
                        self.io.tool_output(f"DEBUG: Added symbols for {rel_fname}")

                # Process javascript files - add function and class definitions
                elif ext == '.js':
                    files_with_symbols.add(rel_fname)
                    file_output = []
                    file_output.append("")
                    file_output.append(f"{rel_fname}:")

                    # Extract functions
                    func_defs = []
                    for i, line in enumerate(lines):
                        if 'function ' in line or '=>' in line:
                            func_defs.append((i, line))

                    # Extract classes
                    class_defs = []
                    for i, line in enumerate(lines):
                        if line.strip().startswith('class '):
                            class_defs.append((i, line))

                    self.io.tool_output(f"DEBUG: Found {len(class_defs)} classes and {len(func_defs)} functions in {rel_fname}")

                    symbols_output = []

                    # Process functions
                    for line_num, line in func_defs:
                        symbols_output.append("⋮")
                        symbols_output.append(f"│{line.rstrip()}")

                        # Add function body
                        for i in range(line_num + 1, min(line_num + 4, len(lines))):
                            context_line = lines[i].rstrip()
                            if not context_line:  # Stop at first empty line
                                break
                            symbols_output.append(f"│{context_line}")

                    # Process classes
                    for line_num, line in class_defs:
                        symbols_output.append("⋮")
                        symbols_output.append(f"│{line.rstrip()}")

                        # Add class body
                        for i in range(line_num + 1, min(line_num + 6, len(lines))):
                            symbols_output.append(f"│{lines[i].rstrip()}")

                    if symbols_output:
                        symbols_output.append("⋮")
                        file_output.extend(symbols_output)
                        all_outputs.extend(file_output)
                        self.io.tool_output(f"DEBUG: Added symbols for {rel_fname}")

                # Fallback to tags
                elif file_tags:
                    files_with_symbols.add(rel_fname)
                    file_output = []
                    file_output.append("")
                    file_output.append(f"{rel_fname}:")

                    symbols_output = []
                    for tag in sorted(file_tags, key=lambda x: x.line):
                        line_num = tag.line
                        self.io.tool_output(f"DEBUG: Processing tag {tag.name} at line {line_num} in {rel_fname}")

                        if line_num < 0 or line_num >= len(lines):
                            self.io.tool_warning(f"DEBUG: Invalid line number {line_num} for {tag.name} in {rel_fname}")
                            continue

                        # Get the line containing the symbol
                        line = lines[line_num]
                        self.io.tool_output(f"DEBUG: Line content: {line}")

                        # Is this a class definition?
                        is_class = "class " in line
                        # Is this a function definition?
                        is_function = "def " in line or "function " in line

                        # Add the symbol with its context
                        symbols_output.append("⋮")

                        # Add the definition line
                        symbols_output.append(f"│{line.rstrip()}")

                        # Add some context (next few lines)
                        context_lines = 3 if is_function else 5 if is_class else 1
                        for i in range(line_num + 1, min(line_num + context_lines + 1, len(lines))):
                            context_line = lines[i].rstrip()
                            if not context_line and not is_class:  # Stop at first empty line unless it's a class
                                break
                            symbols_output.append(f"│{context_line}")

                    if symbols_output:
                        symbols_output.append("⋮")
                        file_output.extend(symbols_output)
                        all_outputs.extend(file_output)
                        self.io.tool_output(f"DEBUG: Added symbols for {rel_fname}")

        self.io.tool_output(f"DEBUG END: Generated {len(all_outputs)} lines of output")

        # Now add the list of files by extension that didn't have symbols
        extension_lists = []
        for ext, files in sorted(files_by_extension.items()):
            remaining_files = [f for f in files if f not in files_with_symbols]
            if remaining_files:
                if ext == "no_extension":
                    ext_header = "Files without extension:"
                else:
                    ext_header = f"{ext} files:"

                file_list = "\n".join(f"  {f}" for f in sorted(remaining_files))
                extension_lists.append(f"{ext_header}\n{file_list}")

        # Combine the extension lists with the symbol maps
        if extension_lists:
            result = "Repository contents:\n\n" + "\n\n".join(extension_lists)
            if all_outputs:
                result += "\n\n" + "\n".join(all_outputs)
        elif all_outputs:
            result = "Repository contents:\n\n" + "\n".join(all_outputs)
        else:
            result = "Repository contents:\n\n"

        # Make sure we have something to return
        if result.strip() == "Repository contents:":
            result = "Repository contents:\n\n"

        # Truncate long lines, in case we get minified js or something else crazy
        result = "\n".join([line[:100] for line in result.splitlines()]) + "\n"

        return result


def find_src_files(directory):
    """
    Find all files in a directory recursively, optimized for large repositories.

    Args:
        directory: Directory to search

    Returns:
        List of absolute paths to all files found
    """
    if not os.path.isdir(directory):
        return [directory]

    src_files = []
    # Common binary file extensions to skip
    binary_extensions = {
        # Compiled code
        '.pyc', '.pyo', '.so', '.o', '.a', '.lib', '.dylib', '.dll', '.exe',
        '.obj', '.jar', '.class', '.pdb', '.ilk', '.bin',
        # Database files
        '.db', '.sqlite', '.sqlite3', '.mdb',
        # Media files
        '.ico', '.gif', '.jpg', '.jpeg', '.png', '.woff', '.woff2', '.ttf', '.eot',
        '.raw', '.bmp', '.tif', '.tiff', '.mp3', '.mp4', '.mov', '.avi',
        '.wmv', '.flv', '.wav', '.webm', '.webp',
        # Archive files
        '.zip', '.tar', '.gz', '.7z', '.rar', '.iso', '.pdf',
        # Other binary files
        '.idx', '.pack', '.lock', '.bin', '.dat', '.cache', '.svg', '.wasm',
        '.min.js', '.min.css', '.min.map', '.map',
    }

    # Common directories to skip
    skip_dirs = {
        # Build artifacts and caches
        '__pycache__', '.git', '.svn', '.hg', '.pytest_cache', '.mypy_cache',
        'node_modules', 'venv', 'env', '.env', '.venv', '.tox', 'dist', 'build',
        'target', 'bin', 'obj', '.idea', '.vscode', '.vs', '__MACOSX',
        # Common large directories
        'vendor', 'third_party', 'third-party', 'ThirdParty', 'External',
        'assets', 'data', 'images', 'img', 'media', 'videos', 'audio',
        'logs', 'log', 'temp', 'tmp', 'cache',
    }

    # Maximum file size to process - 2MB
    # This is a sensible limit for code files (non-generated files are usually much smaller)
    MAX_FILE_SIZE = 2 * 1024 * 1024

    # Maximum number of files to return per directory (safety valve)
    MAX_FILES_PER_DIR = 10000

    # Track progress for large repositories
    total_files_found = 0
    total_dirs_processed = 0

    # Use os.walk with topdown=True to modify dirs in-place
    for root, dirs, files in os.walk(directory, topdown=True):
        total_dirs_processed += 1

        # Skip excluded directories (modify in-place)
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]

        # For very large directories, process only the most likely source code files
        if len(files) > MAX_FILES_PER_DIR:
            files = [f for f in files if os.path.splitext(f)[1].lower() in
                    {'.py', '.js', '.ts', '.cpp', '.c', '.h', '.hpp', '.java',
                     '.scala', '.go', '.rs', '.rb', '.php', '.cs', '.swift',
                     '.kt', '.dart', '.sh', '.bash', '.zsh', '.ps1', '.md'}]

            # Still too many files? Take only the first MAX_FILES_PER_DIR
            if len(files) > MAX_FILES_PER_DIR:
                files = files[:MAX_FILES_PER_DIR]

        for file in files:
            # Skip files with binary extensions
            ext = os.path.splitext(file)[1].lower()
            if ext in binary_extensions:
                continue

            # Skip files that are likely minified or generated
            if (file.endswith('.min.js') or file.endswith('.min.css') or
                file.endswith('.bundle.js') or '.min.' in file):
                continue

            file_path = os.path.join(root, file)

            # Skip very large files
            try:
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE:
                    continue
                elif file_size == 0:  # Skip empty files
                    continue
            except (OSError, IOError):
                continue

            # Skip files that aren't text files (basic check)
            try:
                # Try to read the first 512 bytes for file type checking
                with open(file_path, 'rb') as f:
                    header = f.read(512)

                # Check if file might be binary by looking for null bytes and high ratio of non-printable chars
                if b'\0' in header:
                    # File contains null bytes, likely binary
                    continue

                # Count the ratio of non-printable, non-whitespace ASCII chars
                printable_ratio = sum(32 <= b <= 126 or b in (9, 10, 13) for b in header) / len(header)
                if printable_ratio < 0.7:  # If less than 70% printable, likely binary
                    continue
            except (OSError, IOError):
                continue

            src_files.append(file_path)
            total_files_found += 1

    return src_files


def get_random_color():
    hue = random.random()
    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 0.75)]
    res = f"#{r:02x}{g:02x}{b:02x}"
    return res


def get_scm_fname(lang):
    """
    Find the tree-sitter query file for a given language

    This function attempts to locate the tags query (.scm) file for a specified language
    by searching in multiple possible locations.
    """
    # Normalize language name and define variants
    # Some language parsers use different naming conventions
    lang_variants = {
        "c_sharp": ["csharp", "c#", "c-sharp"],
        "csharp": ["c_sharp", "c#", "c-sharp"],
        "c#": ["c_sharp", "csharp", "c-sharp"],
        "c++": ["cpp", "cplusplus"],
        "cpp": ["c++", "cplusplus"],
        "typescript": ["ts", "tsx"],
        "tsx": ["typescript", "ts"],
        "javascript": ["js", "jsx"],
        "jsx": ["javascript", "js"],
        "java": ["java"],
        "python": ["py"],
        "ruby": ["rb"],
        "golang": ["go"],
        "go": ["golang"],
        "rust": ["rs"],
        "php": ["php"],
        "shell": ["bash", "sh"],
        "bash": ["shell", "sh"],
        "yaml": ["yml"],
        "html": ["html"],
        "css": ["css"],
        "json": ["json"],
        "swift": ["swift"],
        "kotlin": ["kt"],
        "scala": ["scala"],
        "clojure": ["clj"],
        "elixir": ["ex", "exs"],
        "erlang": ["erl"],
        "elm": ["elm"],
        "haskell": ["hs"],
        "ocaml": ["ml"],
        "lua": ["lua"],
        "r": ["r"],
        "dart": ["dart"],
        "markdown": ["md"],
        "sql": ["sql"],
        "d": ["d"],
        "fsharp": ["fs"],
        "groovy": ["groovy"],
        "julia": ["jl"],
        "solidity": ["sol"],
        "perl": ["pl"],
        "raku": ["raku"],
        "racket": ["rkt"],
        "scheme": ["scm"],
        "toml": ["toml"],
        "xml": ["xml"],
    }

    # Add the original language to the variants list
    variants_to_try = [lang] + lang_variants.get(lang, [])

    # Make variants unique in case there are duplicates
    variants_to_try = list(dict.fromkeys(variants_to_try))

    if USING_TSL_PACK:
        # Add commonly used filename patterns
        query_filenames = [f"{v}-tags.scm" for v in variants_to_try]
        query_filenames.extend([f"{v}_tags.scm" for v in variants_to_try])
        query_filenames.extend(["tags.scm"])  # Some languages just use tags.scm

        # List of all possible directories to search
        search_dirs = []

        # Add project-specific directories
        project_dirs = [
            Path(__file__).parent / "queries",
            Path(__file__).parent / "queries" / "tree-sitter-language-pack",
            Path(__file__).parent / "queries" / "tree-sitter-languages",
            Path(__file__).parent / "samples",
        ]
        search_dirs.extend(project_dirs)

        # Try to find in installed packages
        try:
            # Check tree-sitter-language-pack package
            import tree_sitter_language_pack
            package_dir = Path(tree_sitter_language_pack.__file__).parent
            search_dirs.append(package_dir / "queries")
        except (ImportError, AttributeError):
            pass

        # Check for language-specific packages
        for variant in variants_to_try:
            module_names = [
                f"tree_sitter_{variant.replace('-', '_')}",
                f"tree-sitter-{variant.replace('_', '-')}",
            ]

            for module_name in module_names:
                try:
                    module = __import__(module_name)
                    package_dir = Path(module.__file__).parent
                    search_dirs.append(package_dir / "queries")
                except (ImportError, AttributeError):
                    pass

        # Check grep_ast as a fallback
        try:
            import grep_ast
            package_dir = Path(grep_ast.__file__).parent
            search_dirs.append(package_dir / "queries")
        except (ImportError, AttributeError):
            pass

        # Try to find query files in all search directories
        for directory in search_dirs:
            if not directory.exists() or not directory.is_dir():
                continue

            # Try all possible query filenames in each directory
            for filename in query_filenames:
                query_path = directory / filename
                if query_path.exists():
                    return query_path

    # If we're not using TSL pack or couldn't find any queries, let's create a minimal fallback query
    # This will at least capture function and class definitions for common languages
    for variant in variants_to_try:
        if variant in ["python", "py"]:
            # Create a directory for fallback queries if it doesn't exist
            fallback_dir = Path(__file__).parent / "queries" / "fallback"
            fallback_dir.mkdir(exist_ok=True, parents=True)

            # Create minimal Python query file
            fallback_path = fallback_dir / "python-tags.scm"
            if not fallback_path.exists():
                with open(fallback_path, "w") as f:
                    f.write("""
; Minimal Python query for RepoMap
(class_definition
  name: (identifier) @name.definition.class)
(function_definition
  name: (identifier) @name.definition.function)
(identifier) @name.reference
                    """)
            return fallback_path

        elif variant in ["javascript", "js", "jsx"]:
            # Create a directory for fallback queries if it doesn't exist
            fallback_dir = Path(__file__).parent / "queries" / "fallback"
            fallback_dir.mkdir(exist_ok=True, parents=True)

            # Create minimal JavaScript query file
            fallback_path = fallback_dir / "javascript-tags.scm"
            if not fallback_path.exists():
                with open(fallback_path, "w") as f:
                    f.write("""
; Minimal JavaScript query for RepoMap
(class_declaration
  name: (identifier) @name.definition.class)
(function_declaration
  name: (identifier) @name.definition.function)
(identifier) @name.reference
                    """)
            return fallback_path

    # Return None if no file found
    return None


def get_supported_languages_md():
    from grep_ast.parsers import PARSERS

    res = """
| Language | File extension | Repo map | Linter |
|:--------:|:--------------:|:--------:|:------:|
"""
    data = sorted((lang, ex) for ex, lang in PARSERS.items())

    for lang, ext in data:
        fn = get_scm_fname(lang)
        repo_map = "✓" if Path(fn).exists() else ""
        linter_support = "✓"
        res += f"| {lang:20} | {ext:20} | {repo_map:^8} | {linter_support:^6} |\n"

    res += "\n"

    return res


class SimpleIO:
    """Simple IO class to handle tool warnings and outputs"""

    def tool_warning(self, message):
        print(f"WARNING: {message}", file=sys.stderr)

    def tool_output(self, message):
        print(message)

    def tool_error(self, message):
        print(f"ERROR: {message}", file=sys.stderr)

    def read_text(self, fname):
        """Read text from a file"""
        try:
            with open(fname, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            self.tool_error(f"Failed to read {fname}: {e}")
            return None

    def confirm_ask(self, message, default="y", subject=None):
        """Simulate confirm ask by always returning True for CLI tool"""
        return True


class MockModel:
    """Mock model for token counting"""
    def token_count(self, text):
        """Simple token count estimate: 1 token per 4 characters"""
        return len(text) // 4


def main():
    """Main entry point for the repomap command"""
    import argparse
    import datetime
    import re
    import urllib.parse
    import glob

    try:
        from models import Model  # Try to import Model from the app
        import io_utils  # Import our new IO utilities module
        from io_utils import InputOutput
    except ImportError:
        # If running standalone, use mock model
        Model = MockModel
        import io_utils
        from io_utils import InputOutput

    parser = argparse.ArgumentParser(description="Generate a map of a code repository")
    parser.add_argument("files", nargs="*", help="Files or directories to include in the map")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--tokens", "-t", type=int, default=4096, help="Maximum tokens per part (minimum 4096)")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    parser.add_argument("--repo", "-r", help="Repository URL or name (for naming output files)")
    parser.add_argument("--output-dir", default="output", help="Directory to save output files")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress informational output")
    parser.add_argument("--no-split", action="store_true", help="Don't split output into multiple files")
    parser.add_argument("--list-parts", action="store_true", help="List existing repository map parts")

    args = parser.parse_args()

    # Initialize I/O handler
    io = InputOutput(quiet=args.quiet)

    # If list_parts is specified, show the available map parts and exit
    if args.list_parts:
        output_dir = Path(args.output_dir)
        if not output_dir.exists():
            io.tool_error(f"Output directory {args.output_dir} does not exist")
            return 1

        part_files = sorted(glob.glob(str(output_dir / "repomap_*_part*.txt")))
        if not part_files:
            io.tool_output("No repository map parts found")
            return 0

        # Group files by repository name
        repo_parts = {}
        for path in part_files:
            filename = os.path.basename(path)
            match = re.match(r'repomap_([^_]+)_part(\d+)\.txt', filename)
            if match:
                repo_name, part = match.groups()
                if repo_name not in repo_parts:
                    repo_parts[repo_name] = []
                repo_parts[repo_name].append((int(part), path))

        # Display parts for each repository
        io.tool_output("Available repository map parts:")
        for repo_name, parts in sorted(repo_parts.items()):
            parts.sort(key=lambda x: x[0])  # Sort by part number
            io.tool_output(f"\n{repo_name}:")
            for part_num, path in parts:
                file_size = os.path.getsize(path) / 1024  # Size in KB
                io.tool_output(f"  Part {part_num}: {os.path.basename(path)} ({file_size:.1f} KB)")

        return 0

    if not args.files:
        parser.print_help()
        return 1

    # Initialize the language model (for token counting)
    try:
        model = Model("gpt-3.5-turbo")  # Use actual model if available
    except Exception:
        model = MockModel()  # Fallback to mock model

    # We'll use input files directly and let RepoMap handle directory expansion
    chat_fnames = args.files
    other_fnames = []

    # If no_split is specified, set token limit to a large value to ensure everything fits in one file
    token_limit = 1000000 if args.no_split else args.tokens

    # Initialize RepoMap with proper model and IO
    rm = RepoMap(
        root=".",
        io=io,
        verbose=args.verbose,
        main_model=model,
        map_tokens=token_limit
    )

    # Debug mode - print query files found
    if args.debug:
        try:
            from grep_ast.parsers import PARSERS
            io.tool_output("Available language parsers:")
            for ext, lang in sorted(PARSERS.items()):
                query_file = get_scm_fname(lang)
                status = "✓" if query_file else "✗"
                if query_file:
                    io.tool_output(f"{status} {lang} ({ext}): {query_file}")
                else:
                    io.tool_output(f"{status} {lang} ({ext}): No query file found")
        except ImportError:
            io.tool_error("Unable to import grep_ast.parsers - check your installation")
            return 1

    # Extract repo name from URL or use a default name
    repo_name = "repo"
    if args.repo:
        # Extract repo name from URL
        parsed_url = urllib.parse.urlparse(args.repo)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 2:
            repo_name = path_parts[-1]
        else:
            repo_name = path_parts[-1] if path_parts else "repo"
    else:
        # Try to get repo name from current directory
        try:
            repo_name = os.path.basename(os.path.abspath("."))
            # Remove special characters that might cause issues
            repo_name = re.sub(r'[^\w\-]', '_', repo_name)
        except Exception:
            repo_name = "repo"

    # Generate timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Check for memory usage monitoring if verbose
    if args.verbose:
        try:
            import psutil
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024
            io.tool_output(f"Initial memory usage: {initial_memory:.2f} MB")
            track_memory = True
        except ImportError:
            io.tool_output("psutil not installed, memory usage tracking disabled")
            track_memory = False
    else:
        track_memory = False

    # Generate repo map - this will automatically split into parts if needed
    repo_map = rm.get_repo_map([], chat_fnames)

    # Report memory usage after generation if tracking
    if track_memory:
        try:
            current_memory = process.memory_info().rss / 1024 / 1024
            io.tool_output(f"Final memory usage: {current_memory:.2f} MB")
            io.tool_output(f"Memory difference: {current_memory - initial_memory:.2f} MB")
        except (IOError, OSError):
            pass

    if repo_map:
        # If no_split is specified, we need to write the map to a file
        if args.no_split:
            # Create output filename
            output_file = output_dir / f"repomap_{repo_name}_{timestamp}.txt"

            # Write to file using IO helper
            if io.write_text(output_file, repo_map):
                io.tool_output(f"Repository map saved to: {output_file}")
                return 0
            else:
                return 1
        else:
            # Find the map part files that were created
            part_files = sorted(glob.glob(str(output_dir / f"repomap_{repo_name}_part*.txt")))

            if part_files:
                io.tool_output(f"Repository map split into {len(part_files)} parts:")
                for part_file in part_files:
                    file_size = os.path.getsize(part_file) / 1024  # Size in KB
                    io.tool_output(f"  {os.path.basename(part_file)} ({file_size:.1f} KB)")
                return 0
            else:
                io.tool_error("Repository map files were not created")
                return 1
    else:
        io.tool_error("No repository map could be generated")
        return 1


if __name__ == "__main__":
    sys.exit(main())
