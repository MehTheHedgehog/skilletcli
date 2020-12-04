from git import Repo
import sys
import os, stat, shutil
from pathlib import Path
from .path import PathBuilder
import oyaml
from colorama import Fore, Back, Style
import requests

def on_rm_error( func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)

class Github:
    """
    Github remote
    Github provides a wrapper to Git instances and provides indexing/search methods.

    Usage::
        from Remotes import github
        g = Github()
        repos = g.index()
    """
    def __init__(self, topic="skillets", user="PaloAltoNetworks"):
        self.url = "https://api.github.com"
        self.topic = topic
        self.user = user
        self.search_endpoint = "/search/repositories"

    def index(self):
        """
        Retrieves the list of repositories as a list of Git instances.
        :return: [ Github.Git ]
        """
        r = requests.get(self.url + self.search_endpoint, params="q=topic:{}+user:{}".format(self.topic, self.user))
        j = r.json()
        self.check_resp(j)

        repos = []
        for i in j['items']:
            g = Git(i['clone_url'], github_info=i)
            repos.append(g)

        return repos

    def check_resp(self, j):
        if "errors" in j:
            if len(j["errors"]) > 0:
                raise RuntimeError("Github API Call failed! Github err: {}".format(j["message"]))

class Git:
    """
    Git remote

    This class provides an interface to Github repositories containing Skillets or XML snippets.
    """
    def __init__(self, repo_url, store=os.getcwd(), github_info=None):
        """
        Initilize a new Git repo object
        :param repo_url: URL path to repository.
        :param store: Directory to store repository in. Defaults to the current directory.
        :param github_info: (dict): If this object is initialized by the Github class, all the repo attributes from
        Github
        """
        if not check_git_exists():
            print("A git client is required to use this repository.")
            print("See README.md for more details.")
            sys.exit(1)

        self.github_info = github_info
        self.repo_url = repo_url
        self.store = store
        self.Repo = None
        self.name = ""
        self.path = ""
        self.local_builder = None
        #self.local_builder = PathBuilder(self.path)

    def clone(self, name, ow=False, update=False):
        """
        Clone a remote directory into the store.
        :param name: Name of repository
        :param ow: OverWrite, bool, if True will remove any existing directory in the location.
        :return: (string): Path to cloned repository
        """
        if not name:
            raise ValueError("Missing or bad name passed to Clone command.")

        self.update = update
        self.name = name
        path = self.store + os.sep + name
        if path == os.getcwd():
            raise ValueError("For whatever reason, path is set to the current working directory. Die so we don't break anything.")

        self.path = path

        if os.path.exists(path):
            if ow:
                prompt = "{}You have asked to refresh the repository. This will delete everything at {}. Are you sure? [Y/N] {}".format(Fore.RED, self.path, Style.RESET_ALL)
                print(prompt, end="")
                answer = input("")
                if answer == "Y":
                    shutil.rmtree(path,ignore_errors=False, onerror=on_rm_error)
                else:
                    print("{}Refresh specified but user did not agree to overwrite. Exiting.{}".format(Fore.RED, Style.RESET_ALL))
                    sys.exit(1)
            else:
                self.Repo = Repo(path)
                if update:
                    print("Updating repository...")
                    self.Repo.remotes.origin.pull()

                return path
        else:
            print("Cloning into {}".format(path))
            self.Repo = Repo.clone_from(self.repo_url, path)

        self.path = path
        print("Creating local_builder")
        self.local_builder = PathBuilder(path)
        print(self.local_builder)
        return path

    def branch(self, branch_name):
        """
        Checkout the specified branch.

        :param branch_name: Branch to checkout.
        :return: None
        """
        print("Checking out: "+branch_name)
        if self.update:
            print("Updating branch.")
            self.Repo.remotes.origin.pull()
        self.Repo.git.checkout(branch_name)

    def list_branches(self):
        """
        Get a list of remote branches.
        :return: []branch_names: List of branch names (minus remote)
        """
        branches = self.Repo.git.branch('-r').split('\n')
        branch_names = []
        for branch in branches:
            s = branch.split("/")
            branch_names.append(s[len(s)-1])
        return branch_names

    def build(self):
        """
        Build the Skillet object using the git repository.

        Must be called after clone.

        :return: SkilletCollection instance
        """
        if not self.Repo:
            self.clone(self.name)

        return self.local_builder.build(self.name)

    def build_from_local(self, path):
        self.path = path
        self.Repo = "local"
        self.local_builder = PathBuilder(self.path)
        return self.build()

    def get_type_directories(self, template_dir):
        return self.local_builder.get_type_directories(Path(template_dir))

    def get_first_real_dir(self, template_dirs):
        return self.local_builder.get_first_real_dir(Path(template_dirs))

    def get_snippets_in_dir(self, fp):
        return self.local_builder.get_snippets_in_dir(Path(fp))

    def snippets_from_metafile(self, meta_file):
        return self.local_builder.snippets_from_metafile(Path(meta_file))

    def validate_snippet_meta(self, snippet_def, rel_dir):
        return self.local_builder.validate_snippet_meta(snippet_def, Path(rel_dir))

    def is_snippet_dir(self, fp):
        return self.local_builder.is_snippet_dir(Path(fp))

def check_git_exists():
    return shutil.which("git")
