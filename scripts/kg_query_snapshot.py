from rdflib import Graph

g = Graph()
g.parse('kg/schemas/core.ttl', format='turtle')

q = '''
SELECT ?agent ?capability ?status ?recovery_attempts WHERE {
  ?agent a <http://example.org/core#Agent> .
  ?agent <http://example.org/core#hasCapability> ?capability .
  OPTIONAL { ?agent <http://example.org/core#hasRecoveryStatus> ?status . }
  OPTIONAL { ?agent <http://example.org/core#hasRecoveryAttempts> ?recovery_attempts . }
}
'''

for row in g.query(q):
    print([str(x) for x in row]) 