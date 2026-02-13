PROMPT_TEMPLATE = """
    You are a senior code documentation engineer.
    Your task is to generate a comprehensive, professional Concise comment 
    for the following {language} code snippet.

    Target Node Name: {node_name}
    Node Type: {node_type}

    Existing Comment: {existing_comment}

    Source Code:
    {source_code}

    Requirements:
    1. ONLY Summarize the core functionality.
    2. If existing comments are present, refine and standardize them.
    3. OUTPUT MUST BE A VALID JSON OBJECT.
    4.The comments you output must be within 100 tokens.
    5. The JSON key MUST be exactly "{node_name}". 
    6. The JSON value should be the comment string (can be multi-line).
    7.If the comment exceeds 70 characters, it will be displayed in multiple 
      lines. Each line is separated by "\n", and the number of characters in 
      each line is approximately 70.

    Example Output:
    {{
        "{node_name}": "Concise comment here..."
    }}

    Strictly output valid JSON only.
    """