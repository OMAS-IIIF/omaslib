from omaslib.src.helpers.omaserror import OmasError


class SemanticVersion:
    __major: int
    __minor: int
    __patch: int

    def __init__(self, major: int = 1, minor: int = 0, patch: int = 0):
        self.__major = major
        self.__minor = minor
        self.__patch = patch

    def __str__(self) -> str:
        return f"{self.__major}.{self.__minor}.{self.__patch}"

    def __repr__(self) -> str:
        return f"SemanticVersion({self.__major}, {self.__minor}, {self.__patch})"

    def __eq__(self, other: 'SemanticVersion') -> bool:
        return self.__major == other.__major and self.__minor == other.__minor and self.__patch == other.__patch

    def __ne__(self, other: 'SemanticVersion') -> bool:
        return self.__major != other.__major or self.__minor != other.__minor or self.__patch != other.__patch

    def __gt__(self, other: 'SemanticVersion') -> bool:
        if self.__major > other.__major:
            return True
        if self.__major == other.__major and self.__minor > other.__minor:
            return True
        if self.__major == other.__major and self.__minor == other.__minor and self.__patch > other.__patch:
            return True
        return False

    def __ge__(self, other: 'SemanticVersion') -> bool:
        if self.__major >= other.__major:
            return True
        if self.__major == other.__major and self.__minor >= other.__minor:
            return True
        if self.__major == other.__major and self.__minor == other.__minor and self.__patch >= other.__patch:
            return True
        return False

    def __lt__(self, other: 'SemanticVersion') -> bool:
        if self.__major < other.__major:
            return True
        if self.__major == other.__major and self.__minor < other.__minor:
            return True
        if self.__major == other.__major and self.__minor == other.__minor and self.__patch < other.__patch:
            return True
        return False

    def __le__(self, other: 'SemanticVersion') -> bool:
        if self.__major <= other.__major:
            return True
        if self.__major == other.__major and self.__minor <= other.__minor:
            return True
        if self.__major == other.__major and self.__minor == other.__minor and self.__patch <= other.__patch:
            return True
        return False

    @classmethod
    def fromString(cls, versionstring: str) -> 'SemanticVersion':
        try:
            major, minor, patch = versionstring.split(".")
            return cls(int(major), int(minor),int(patch) )
        except ValueError as err:
            raise OmasError(f'Invalid version string: "{versionstring}": {err}')

    def increment_patch(self):
        self.__patch += 1

    def increment_minor(self):
        self.__minor += 1
        self.__patch = 0

    def increment_major(self):
        self.__major += 1
        self.__minor = 0
        self.__patch = 0

