import rdflib

def validate_ttl_file(path: str):
    """
    Validate a Turtle (.ttl) file for RDF/OWL syntax errors.
    Returns (is_valid: bool, message: str)
    """
    try:
        g = rdflib.Graph()
        g.parse(path, format='turtle')
        return True, "Valid Turtle file."
    except Exception as e:
        return False, f"Invalid Turtle file: {str(e)}" 