from datetime import datetime
from rdflib import URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD

ARTIFACT = Namespace("http://example.org/dMaster/artifact#")

class Artifact:
    def __init__(self, artifact_id, content, author, timestamp=None):
        self.artifact_id = artifact_id
        self.content = content
        self.author = author
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_triples(self):
        uri = ARTIFACT[self.artifact_id]
        return [
            (uri, RDF.type, ARTIFACT.Artifact),
            (uri, ARTIFACT.content, Literal(self.content)),
            (uri, ARTIFACT.author, Literal(self.author)),
            (uri, ARTIFACT.timestamp, Literal(self.timestamp, datatype=XSD.dateTime)),
        ] 