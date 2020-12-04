from .skillet import SkilletCollection, SnippetStack, Snippet

import os
from pathlib import Path

import oyaml

class PathBuilder:
    """
    Path 

    This class provide abstract layer to build skillets from local path.
    """
    def __init__(self, path):

        if isinstance(path, Path):
            self.path = path
        elif isinstance(path, str):
            self.path = Path(path)
        else:
            raise ValueError("PathBuilder path should be either sting or Path object!")

        if not self.path.exists():
            raise ValueError("Provided path not exist!")

    def build(self, name):
        # The following section is all hard coded pointers to important stuff #
        #   We expect all of these files in every skillet structure to work.  #
        template_dirs = [
            self.path.joinpath("templates"),
            self.path
        ]

        # End static path definitions #
        # Expects the following structure
        # root/SKILLET_TYPE/SNIPPET_DIR/
        # A SkilletColleciton will be created for each SKILLET_TYPE
        # Populated with every snippet from SKILLET_TYPE/SNIPPET_DIR/
        # For a SKILLET_TYPE directory to be complete, it MUST contain a meta file for each SNIPPET_DIR

        template_dir = self._get_first_real_dir(template_dirs)
        skillet_types = self._get_type_directories(template_dir)
        sc = SkilletCollection(name)

        # This splits all the snippet directories into SnippetStack instances.
        # It uses the metadata 'type' to then add them to the correct skillet (usually 'panosxml' or 'panorama')
        for name, fp in skillet_types.items():
            snippet_stacks = self._get_snippets_in_dir(fp)
            for ss_name, ss in snippet_stacks.items():
                t = ss.metadata['type']
                sk = sc.new_skillet(t, t, ".*")
                sk.add_snippets(snippet_stacks)

        return sc

    def _get_type_directories(self, template_dir):
        skillet_types = {}
        for directory in template_dir.iterdir():
            if not directory.is_file():
                # If directory is a valid type
                if directory.name in ['panos', 'panorama']:
                    skillet_types[directory] = directory
                # Otherwise, if the directory is a snippet directory default to PANOS
                elif self._is_snippet_dir(directory):
                    skillet_types['panos'] = template_dir

        return skillet_types

    def _get_first_real_dir(self, template_dirs):
        """
        Given a list of directories, return the first directory that exists in the system
        :param template_dirs (list): list of directories.
        """
        # Resolve the specified template directories to actual directories
        for template_dir in template_dirs:
            if template_dir.is_dir():
                return template_dir

    def _get_snippets_in_dir(self, fp : Path):
        snippet_dirs = {}

        for directory in fp.iterdir():
            if not directory.is_file():
                if self._is_snippet_dir(directory):
                    snippet_dirs[directory.name] = directory

        snippets_map = {}
        for dir_name, snippet_dir in snippet_dirs.items():
            meta_file = snippet_dir / ".meta-cnc.yaml"
            if (meta_file.exists() and meta_file.is_file()):
                with meta_file.open() as mf:
                    metadata = oyaml.safe_load(mf.read())
                    snippets = self._snippets_from_metafile(meta_file)
                    if len(snippets) > 0:
                        ss = SnippetStack(snippets, metadata)
                        snippets_map[dir_name] = ss

        return snippets_map

    def _snippets_from_metafile(self, meta_file : Path):
        rel_dir = meta_file.parent
        with meta_file.open() as meta_openfile:
            metadata = oyaml.safe_load(meta_openfile.read())
            if "snippets" not in metadata:
                raise ValueError("Malformed metadata file: {}. Missing snippet definition.".format(meta_file))

            snippets = []

            for snippet_def in metadata["snippets"]:
                # This validates the snippet metadata contains all the required information
                if self._validate_snippet_meta(snippet_def, rel_dir):
                    snippet_file = rel_dir / snippet_def["file"]
                    snippet_xpath = snippet_def["xpath"]
                    with snippet_file.open() as snippet_openfile:
                        s = Snippet(snippet_xpath, snippet_openfile.read())
                        s.name = snippet_def["name"]
                        s.set_metadata(metadata)
                        snippets.append(s)

        return snippets

    def _validate_snippet_meta(self, snippet_def, rel_dir):
        snippet_fields = ["file", "xpath"]
        # Validate all the required fields are there
        for sf in snippet_fields:
            if sf not in snippet_def:
                return False

        # Validate the values are valid
        snippet_file = rel_dir / snippet_def["file"]
        if (not snippet_file.exists() and not snippet_file.is_file()):
            return False

        return True

    def _is_snippet_dir(self, fp):
        """
        Check if the directory at fp is a snippet directory
        """
        meta_file = fp.joinpath(".meta-cnc.yaml")
        return (meta_file.exists() and meta_file.is_file())