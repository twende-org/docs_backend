def get_document_schema(doc_type):
    """
    Returns the required fields for a given document type.
    This serves as the single source of truth for document structure.
    """
    schemas = {
        'QUOTATION': {
            'required': ['client_name', 'items', 'total'],
            'description': 'Standard quotation with line items and total amount.'
        },
        'PROFORMA': {
            'required': ['client_name', 'items', 'total', 'bank_details'],
            'description': 'Proforma invoice including bank details for payment.'
        },
        'AFFIDAVIT': {
            'required': ['declarant_name', 'id_number', 'facts'],
            'description': 'Legal affidavit with declarant details and sworn facts.'
        },
        'CONTRACT': {
            'required': ['party_a', 'party_b', 'terms'],
            'description': 'Simple contract between two parties.'
        },
        'LETTER': {
            'required': ['recipient_name', 'subject', 'body'],
            'description': 'General business or personal letter.'
        },
        'EVENT_PROGRAM': {
            'required': ['event_name', 'date', 'schedule'],
            'description': 'Schedule of events for a program.'
        },
    }
    return schemas.get(doc_type, {'required': [], 'description': 'Generic document'})
