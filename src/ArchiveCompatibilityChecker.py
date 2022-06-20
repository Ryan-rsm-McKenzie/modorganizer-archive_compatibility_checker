import dataclasses
import enum
import mobase
import pathlib
import struct
import typing


@enum.unique
class Problem(enum.IntEnum):
    NONE = enum.auto()
    NOT_A_FILE = enum.auto()
    WRONG_EXTENSION = enum.auto()
    WRONG_FORMAT = enum.auto()


@enum.unique
class FileFormat(enum.IntEnum):
    UNKNOWN = enum.auto()
    TES3 = enum.auto()
    TES4 = enum.auto()
    FO3 = enum.auto()
    SSE = enum.auto()
    FO4 = enum.auto()


@dataclasses.dataclass
class ProblemArchive:
    path: pathlib.Path
    problem: Problem


@dataclasses.dataclass
class Description:
    short: str
    long: str


class ArchiveCompatibilityChecker(mobase.IPluginDiagnose):
    def __init__(self):
        super().__init__()
        self.__organizer: mobase.IOrganizer = None
        self.__archives: typing.List[ProblemArchive] = []

        self.__descriptions = {
            Problem.NOT_A_FILE: Description(
                "Invalid archive file detected",
                "The following archives are not valid files:{}"),
            Problem.WRONG_EXTENSION: Description(
                "Incompatible archive extensions detected",
                "The following archives are using an extension meant for a different game:{}"),
            Problem.WRONG_FORMAT: Description(
                "Incompatible archive formats detected",
                "The following archives are using the wrong format. They probably need to be repacked for the current game:{}"),
        }

        self.__supportedGames = {
            "Morrowind",
            "Oblivion",
            "Fallout 3",
            "New Vegas",
            "Skyrim",
            "Fallout 4",
            "Skyrim Special Edition",
            "Skyrim VR",
            "Fallout 4 VR",
        }

        self.__gameToExt = {game: ".bsa" for game in self.__supportedGames}
        self.__gameToExt["Fallout 4"] = ".ba2"
        self.__gameToExt["Fallout 4 VR"] = ".ba2"

        self.__gameToFmt = {game: FileFormat.UNKNOWN for game in self.__supportedGames}
        self.__gameToFmt["Morrowind"] = FileFormat.TES3
        self.__gameToFmt["Oblivion"] = FileFormat.TES4
        self.__gameToFmt["Fallout 3"] = FileFormat.FO3
        self.__gameToFmt["New Vegas"] = FileFormat.FO3
        self.__gameToFmt["Skyrim"] = FileFormat.FO3
        self.__gameToFmt["Fallout 4"] = FileFormat.FO4
        self.__gameToFmt["Skyrim Special Edition"] = FileFormat.SSE
        self.__gameToFmt["Skyrim VR"] = FileFormat.SSE
        self.__gameToFmt["Fallout 4 VR"] = FileFormat.FO4

        self.__magics = {
            0x100: FileFormat.TES3,
            0x00415342: FileFormat.TES4,
            0x58445442: FileFormat.FO4,
        }

        self.__tes4Versions = {
            103: FileFormat.TES4,
            104: FileFormat.FO3,
            105: FileFormat.SSE,
        }

        self.__u32 = struct.Struct("<I")

    def author(self) -> str:
        return "Ryan McKenzie"

    def description(self):
        return "Checks archives (.bsa/.ba2 files) to verify they are compatible with the current game."

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        return True

    def name(self) -> str:
        return "Archive Compatibility Checker"

    def settings(self) -> typing.List[mobase.PluginSetting]:
        return []

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.prealpha)

    def activeProblems(self) -> typing.List[int]:
        self.__archives = list(self.__listBadArchives())
        return list({x.problem.value for x in self.__archives})

    def fullDescription(self, key: int) -> str:
        problem = Problem(key)
        if problem in self.__descriptions:
            description = self.__descriptions[problem].long
            archives = [x.path.name for x in self.__archives if x.problem == problem]
            return description.format("<br><br>•  " + ("<br>•  ".join(archives)))
        else:
            raise IndexError

    def hasGuidedFix(self, key: int) -> bool:
        problem = Problem(key)
        if problem != Problem.NONE:
            return False
        else:
            raise IndexError

    def shortDescription(self, key: int) -> str:
        problem = Problem(key)
        if problem in self.__descriptions:
            return self.__descriptions[problem].short
        else:
            raise IndexError

    def startGuidedFix(self, key: int):
        raise ValueError

    def __getCurrentGame(self) -> str:
        return self.__organizer.managedGame().gameName()

    def __listBadArchives(self) -> typing.Generator[ProblemArchive, None, None]:
        for file in self.__organizer.findFiles("", "*.b[sa][a2]"):
            path = pathlib.Path(file)
            problem = self.__validateArchive(path)
            if problem != Problem.NONE:
                yield ProblemArchive(path, problem)

    def __validateArchive(self, path: pathlib.Path) -> Problem:
        if not path.is_file():
            return Problem.NOT_A_FILE
        elif path.suffix != self.__gameToExt[self.__getCurrentGame()]:
            return Problem.WRONG_EXTENSION
        elif self.__getFileFormat(path) != self.__gameToFmt[self.__getCurrentGame()]:
            return Problem.WRONG_FORMAT
        else:
            return Problem.NONE

    def __getFileFormat(self, path: pathlib.Path) -> FileFormat:
        stat = path.stat()

        if stat.st_size < 4:
            return FileFormat.UNKNOWN

        file = path.open(mode="rb")
        magic = self.__u32.unpack(file.read(4))[0]
        fmt = self.__magics.get(magic, FileFormat.UNKNOWN)

        if fmt == FileFormat.TES4:
            if stat.st_size < 8:
                return FileFormat.UNKNOWN
            else:
                version = self.__u32.unpack(file.read(4))[0]
                return self.__tes4Versions.get(version, FileFormat.UNKNOWN)
        else:
            return fmt


def createPlugin():
    return ArchiveCompatibilityChecker()
