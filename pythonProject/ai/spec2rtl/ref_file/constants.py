from enum import Enum
class SpecNodeType(Enum):
    """
    SpecNodeType
    """
    OP_CODE = "encoding"
    PORT = "port"
    STATE = "state"
    GLSRY = "glossary"