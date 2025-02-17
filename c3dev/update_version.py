#!/usr/bin/env python
import glob
import os
from os import path

import click

__author__ = "Daniel McDonald"
__copyright__ = "Copyright 2007-2019, The Cogent Project"
__credits__ = ["Daniel McDonald", "Gavin Huttley"]
__license__ = "GPL"
__version__ = "3.0a2"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "Development"


class VersionUpdater(object):
    """Handles version update of files contained within the PyCogent tree"""

    def __init__(
        self,
        rootdir=None,
        version=None,
        is_release=False,
        verbose=False,
        mock_run=False,
        version_short=None,
    ):
        self.rootdir = rootdir
        self.version = version
        self.version_short = version_short
        self.version_tuple = tuple(self.version.split("."))
        self.is_release = is_release
        self.verbose = verbose
        self.mock_run = mock_run

        self.codes_directory = path.join(self.rootdir, "src/cogent3")
        self.tests_directory = path.join(self.rootdir, "tests")
        self.doc_directory = path.join(self.rootdir, "doc")
        self.includes_directory = path.join(self.rootdir, "src/include")

        if not os.access(path.join(self.codes_directory, "__init__.py"), os.R_OK):
            raise IOError("Could not locate cogent3/__init__.py")
        if not os.access(path.join(self.tests_directory, "__init__.py"), os.R_OK):
            raise IOError("Could not locate tests/__init__.py")
        if not os.access(path.join(self.doc_directory, "conf.py"), os.R_OK):
            raise IOError("Could not locate doc/conf.py")

    def _get_test_files(self):
        """Support method, provides relative locations for test files"""
        for dirpath, dirnames, filenames in os.walk(self.tests_directory):
            for f in filenames:
                if f.endswith(".py"):
                    yield (path.join(dirpath, f), "Python")

    def _get_code_files(self):
        """Support method, provides relative locations for code files

        Yields file name and file type
        """
        for dirpath, dirnames, filenames in os.walk(self.codes_directory):
            for f in filenames:
                rel_name = path.join(dirpath, f)
                if f.endswith(".py"):
                    yield rel_name, "Python"
                elif f.endswith(".pyx"):
                    yield rel_name, "Cython"
                elif f.endswith(".c"):
                    yield rel_name, "C"

    def _get_doc_files(self):
        """Support method, provides relative locations for test files

        Only yields conf.py currently
        """
        return [(path.join(self.doc_directory, "conf.py"), "Python")]

    def _get_include_files(self):
        """Support method, provides relative locations for include files

        Yields file name and file type
        """
        for dirpath, dirnames, filenames in os.walk(self.includes_directory):
            for f in filenames:
                rel_name = path.join(dirpath, f)
                if f.endswith(".pyx"):
                    yield (rel_name, "Cython")
                elif f.endswith(".h"):
                    yield (rel_name, "header")
                else:
                    pass

    def _update_python_file(self, lines, filename):
        """Updates the __version__ string of a Python file"""
        found_version_line = False
        for lineno, line in enumerate(lines):
            if line.startswith("__version__"):
                found_version_line = True
                break
        if found_version_line:
            if self.verbose:
                print("Version string found on line %d" % lineno)
            lines[lineno] = '__version__ = "%s"\n' % self.version
        else:
            print("No version string found in %s" % filename)
        return (lines, found_version_line)

    def _update_properties_file(self, lines, filename):
        """Updates version information in specific properties files

        Expects the properties file to be in "key=value" lines
        """
        found_version_line = False
        if filename.endswith("cogent3-requirements.txt"):
            for lineno, line in enumerate(lines):
                if "packages/source/c/cogent3" in line:
                    found_version_line = True
                    break
        if found_version_line:
            if self.verbose:
                print("Version string found on line %d" % lineno)
            http_base = lines[lineno].rsplit("/", 1)[0]
            lines[lineno] = "%s/PyCogent-%s.tgz\n" % (http_base, self.version)
        else:
            print("No version string found in %s" % filename)
        return (lines, found_version_line)

    def _update_doc_conf_file(self, lines, filename):
        """Updates doc/conf.py file"""
        versionline = None
        releaseline = None

        for lineno, line in enumerate(lines):
            if line.startswith("version"):
                versionline = lineno
            if line.startswith("release"):
                releaseline = lineno
            if versionline is not None and releaseline is not None:
                break

        if versionline is None:
            print("No version string found in doc/conf.py")
        else:
            if self.verbose:
                print("Version string found on line %d" % versionline)
            lines[versionline] = 'version = "%s"\n' % self.version_short

        if releaseline is None:
            print("No release string found in doc/conf.py")
        else:
            if self.verbose:
                print("Release string found on line %d" % releaseline)
            lines[releaseline] = 'release = "%s"\n' % self.version

        return (lines, versionline and releaseline)

    def _update_cython_file(self, lines, filename):
        """Updates __version__ within a pyx file"""
        found_version_line = False
        for lineno, line in enumerate(lines):
            if line.startswith("__version__"):
                found_version_line = True
                break
        if found_version_line:
            if self.verbose:
                print("Version string found on line %d" % lineno)
            lines[lineno] = '__version__ = "%s"\n' % str(self.version_tuple)
        else:
            print("No version string found in %s" % filename)
        return (lines, found_version_line)

    def _update_header_file(self, lines, filename):
        """Updates a C header file"""
        found_version_line = False
        for lineno, line in enumerate(lines):
            if line.startswith("#define PYCOGENT_VERSION"):
                found_version_line = True
                break
        if found_version_line:
            if self.verbose:
                print("Version string found on line %d" % lineno)
            lines[lineno] = '#define PYCOGENT_VERSION "%s"\n' % self.version
        else:
            print("No version string found in %s" % filename)
        return (lines, found_version_line)

    def _update_c_file(self, lines, filename):
        """Updates a C file"""
        # same as C header...
        return self._update_header_file(lines, filename)

    def _file_writer(self, lines, filename):
        """Handles writing out to the file system"""
        if self.mock_run:
            return

        if self.verbose:
            print("Writing file %s" % filename)

        with open(filename, "w") as updated_file:
            updated_file.write("".join(lines))

    def update_doc_files(self):
        """Updates version strings in documentation files

        So far we only update conf.py
        """
        for filename, filetype in self._get_doc_files():
            lines = open(filename).readlines()

            if self.verbose:
                print("Reading %s" % filename)

            if filename.endswith("conf.py"):
                lines, write_out = self._update_doc_conf_file(lines, filename)
            else:
                raise TypeError("Unknown doc file type: %s" % filetype)

            if write_out:
                self._file_writer(lines, filename)

    def update_include_files(self):
        """Updates version strings in include files"""

        for filename, filetype in self._get_include_files():
            lines = open(filename).readlines()
            if self.verbose:
                print("Reading %s" % filename)

            if filetype == "Cython":
                lines, write_out = self._update_cython_file(lines, filename)
            elif filetype == "header":
                lines, write_out = self._update_header_file(lines, filename)
            else:
                raise TypeError("Unknown include file type %s" % filetype)

            if write_out:
                self._file_writer(lines, filename)

    def update_test_files(self):
        """Updates version strings in test files"""

        for filename, filetype in self._get_test_files():
            lines = open(filename).readlines()
            if self.verbose:
                print("Reading %s" % filename)

            if filetype == "Python":
                lines, write_out = self._update_python_file(lines, filename)
            else:
                raise TypeError("Unknown test file type %s" % filetype)

            if write_out:
                self._file_writer(lines, filename)

    def update_code_files(self):
        """Updates version strings in code files"""

        # if this annoying slow, could probably drop to bash or soemthing
        # for a search/replace
        for filename, filetype in self._get_code_files():
            lines = open(filename).readlines()
            if self.verbose:
                print("Reading %s" % filename)

            if filetype == "Python":
                lines, write_out = self._update_python_file(lines, filename)
            elif filetype == "Cython":
                lines, write_out = self._update_cython_file(lines, filename)
            elif filetype == "C":
                lines, write_out = self._update_c_file(lines, filename)
            else:
                raise TypeError("Unknown code file type %s" % filetype)

            if write_out:
                self._file_writer(lines, filename)


@click.command()
@click.option(
    "-d",
    "--rootdir",
    default="",
    type=click.Path(exists=True),
    help="root directory for project",
)
@click.option(
    "-v", "--version", required=True, default="", help="new version"
)  # todo allow auto date based version?
@click.option("-vs", "--version_short", default="")
@click.option("--is_release", is_flag=True)
@click.option("--verbose", is_flag=True)
@click.option("-mr", "--mock_run", is_flag=True)
def main(rootdir, version, version_short, is_release, verbose, mock_run):
    """Support for updating version strings in the a source tree

    All .py, .pyx, and .c files descending from rootdir will be updated
    """
    if not version:
        click.secho("No version info provided", fg="red")
        exit()

    updater = VersionUpdater(
        rootdir=rootdir,
        version=version,
        version_short=version_short,
        is_release=is_release,
        verbose=verbose,
        mock_run=mock_run,
    )

    updater.update_code_files()
    updater.update_test_files()
    updater.update_doc_files()
    updater.update_include_files()


if __name__ == "__main__":
    main()
