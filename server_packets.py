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
    busWidthLeft: NotRequired[float]
    busWidthRight: NotRequired[float]
    completed: NotRequired[bool]


# response
class RoutingProgressResponse(TypedDict):
    endpoint: Literal["routingProgress"]
    error: NotRequired[RoutingProgressResponseError]
    result: NotRequired[RoutingProgressResponseResult]


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
