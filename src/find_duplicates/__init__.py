# find_duplicates package
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("find-duplicates")
except PackageNotFoundError:
    __version__ = "0.5.0"

