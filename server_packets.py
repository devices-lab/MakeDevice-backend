from typing import TypedDict, List, Literal, NotRequired

"""
Types used for communication between the client and server
This is based on the frontend's `networking/packetTypes.ts` interfaces.
"""

# Incoming Request Types


class RoutingStartRequest(TypedDict):
    endpoint: Literal["routingStart"]
    project: str  # Project serialized as JSON, TODO: Define a proper Project type, subset of values relevant to the backend


class RoutingProgressRequest(TypedDict):
    endpoint: Literal["routingProgress"]
    jobId: str


class PCBArtifactRequest(TypedDict):
    endpoint: Literal["pcbArtifact"]
    jobId: str
    uploadToFabHouse: NotRequired[bool]


class RouteSegment(TypedDict):
    layer: str          # e.g. "F_Cu.gtl" / "B_Cu.gbl"
    net: str
    startX: float
    startY: float
    endX: float
    endY: float
    width: float


class RouteVia(TypedDict):
    net: str
    x: float
    y: float


class RoutePayload(TypedDict):
    segments: List[RouteSegment]
    vias: List[RouteVia]
    totalBusesWidth: NotRequired[float]
    connectedSocketsCount: NotRequired[int]


class ArtifactsFromRouteRequest(TypedDict):
    endpoint: Literal["artifactsFromRoute"]
    project: str   # Same .MakeDevice JSON shape as routingStart.project
    route: RoutePayload


class ArtifactsFromRouteResponseResult(TypedDict):
    jobId: str


class ArtifactsFromRouteResponseError(TypedDict):
    message: str


class ArtifactsFromRouteResponse(TypedDict):
    endpoint: Literal["artifactsFromRoute"]
    error: NotRequired[ArtifactsFromRouteResponseError]
    result: NotRequired[ArtifactsFromRouteResponseResult]


# Outgoing Response Types


class RoutingStartResponseResult(TypedDict):
    jobId: str


class RoutingStartResponseError(TypedDict):
    message: str


# response
class RoutingStartResponse(TypedDict):
    endpoint: Literal["routingStart"]
    error: NotRequired[RoutingStartResponseError]
    result: NotRequired[RoutingStartResponseResult]


class RoutingProgressResponseError(TypedDict):
    message: str
    failedModuleIds: List[str]
    succeededModuleIds: NotRequired[List[str]]


class RoutingProgressResponseResult(TypedDict):
    progress: float
    routingImage: NotRequired[str]  # Base64 encoded image
    routingImageFront: NotRequired[str]  # Base64 encoded front preview image
    routingImageBack: NotRequired[str]  # Base64 encoded back preview image
    busWidthLeft: NotRequired[float]
    busWidthRight: NotRequired[float]
    completed: NotRequired[bool]


# response
class RoutingProgressResponse(TypedDict):
    endpoint: Literal["routingProgress"]
    error: NotRequired[RoutingProgressResponseError]
    result: NotRequired[RoutingProgressResponseResult]
    issues: NotRequired[List[str]]


class PCBArtifactResponseResult(TypedDict):
    zipFile: str  # Base64 encoded zip file
    fabricationUrl: NotRequired[str]


class PCBArtifactResponseError(TypedDict):
    message: str


# response
class PCBArtifactResponse(TypedDict):
    endpoint: Literal["pcbArtifact"]
    error: NotRequired[PCBArtifactResponseError]
    result: NotRequired[PCBArtifactResponseResult]
