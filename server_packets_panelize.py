from typing import TypedDict, List, Literal, NotRequired

"""
Types used for communication between the client and server.
Mirrors frontend `networking/packetTypes.ts`.
"""


# -----------------------------
# Incoming Request Types
# -----------------------------

class Vec2(TypedDict):
    x: float
    y: float

class FabSpec(TypedDict):
    count: Vec2
    step: Vec2
    viaHoleDiameter: float
    biteHoleDiameter: float
    fabRailHoleDiameter: float

class Layer(TypedDict):
    side: str
    type: str

class FileTextLayer(TypedDict):
    layer: Layer
    content: str
    name: str

class PanelizeStartRequest(TypedDict):
    endpoint: Literal["panelizeStart"]
    fileTextLayers: List[FileTextLayer]
    fabSpec: FabSpec
    boardOutlineD: str
    gerberOrigin: Vec2
    vias: List[Vec2]
    biteHoles: List[Vec2]
    fabRailHoles: List[Vec2]
    svgCopperTop: str
    svgCopperBottom: str
    soldermaskTop: str
    soldermaskBottom: str
    vcut: str


class PanelizeProgressRequest(TypedDict):
    endpoint: Literal["panelizeProgress"]
    jobId: str


class PCBArtifactRequest(TypedDict):
    endpoint: Literal["pcbArtifact"]
    jobId: str
    uploadToFabHouse: NotRequired[bool]


# -----------------------------
# Outgoing Response Types
# -----------------------------


class PanelizeStartResponseResult(TypedDict):
    jobId: str


class PanelizeStartResponseError(TypedDict):
    message: str


class PanelizeStartResponse(TypedDict):
    endpoint: Literal["panelizeStart"]
    error: NotRequired[PanelizeStartResponseError]
    result: NotRequired[PanelizeStartResponseResult]


class PanelizeProgressResponseError(TypedDict):
    message: str


class PanelizeProgressResponseResult(TypedDict):
    progress: float
    completed: NotRequired[bool]


class PanelizeProgressResponse(TypedDict):
    endpoint: Literal["panelizeProgress"]
    error: NotRequired[PanelizeProgressResponseError]
    result: NotRequired[PanelizeProgressResponseResult]


class PCBArtifactResponseResult(TypedDict):
    zipFile: str
    fabricationUrl: NotRequired[str]


class PCBArtifactResponseError(TypedDict):
    message: str


class PCBArtifactResponse(TypedDict):
    endpoint: Literal["pcbArtifact"]
    error: NotRequired[PCBArtifactResponseError]
    result: NotRequired[PCBArtifactResponseResult]
