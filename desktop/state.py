"""UI request fences, independent of Tk and of canonical backend state."""
from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class Ticket:
    generation: int
    request_id: str
    operation: str
    namespace: str
    query_revision: int
    identity: tuple


class Fence:
    def __init__(self):
        self.generation = 0
        self.query_revision = 0
        self.namespace = ''
        self.identity = ()
        self.active = None
        self.closed = False

    def invalidate(self, *, namespace=None, reconnect=False, identity=None):
        self.generation += 1
        self.query_revision += 1
        if namespace is not None:
            self.namespace = namespace
        if reconnect:
            self.identity = ()
        if identity is not None:
            self.identity = tuple(sorted(identity.items()))
        self.active = None

    def begin(self, operation):
        self.active = Ticket(self.generation, uuid.uuid4().hex, operation,
                             self.namespace, self.query_revision, self.identity)
        return self.active

    def accepts(self, ticket):
        return (not self.closed and ticket == self.active and
                ticket.generation == self.generation and ticket.namespace == self.namespace and
                ticket.query_revision == self.query_revision and ticket.identity == self.identity)

    def close(self):
        self.invalidate(reconnect=True)
        self.closed = True
