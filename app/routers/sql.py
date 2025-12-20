"""
SQL validation router with endpoint for PostgreSQL query validation.
"""
from fastapi import APIRouter, HTTPException
import sqlparse
from sqlparse import sql, tokens

from app.models import SQLValidationRequest, SQLValidationResponse

router = APIRouter(prefix="/sql", tags=["sql"])


@router.post("/validate", response_model=SQLValidationResponse)
async def validate_sql_query(request: SQLValidationRequest):
    """
    Validate a PostgreSQL SQL query.
    
    Checks if the query has valid SQL syntax and can be parsed.
    Returns the formatted query and query type if valid, or an error message if invalid.
    
    Args:
        request: SQLValidationRequest with the query to validate
        
    Returns:
        SQLValidationResponse: Validation result with formatted query and error details
    """
    query = request.query.strip()
    
    if not query:
        return SQLValidationResponse(
            valid=False,
            query=query,
            error_message="Query cannot be empty"
        )
    
    try:
        # Parse the SQL query
        parsed = sqlparse.parse(query)
        
        if not parsed:
            return SQLValidationResponse(
                valid=False,
                query=query,
                error_message="Unable to parse query - invalid SQL syntax"
            )
        
        # Get the first statement
        statement = parsed[0]
        
        # Check for basic syntax errors
        if not statement.tokens:
            return SQLValidationResponse(
                valid=False,
                query=query,
                error_message="Query contains no valid SQL tokens"
            )
        
        # Determine query type
        query_type = None
        for token in statement.tokens:
            if token.ttype in (tokens.Keyword.DML, tokens.Keyword.DDL):
                query_type = token.value.upper()
                break
            elif isinstance(token, sql.Identifier) or token.ttype == tokens.Keyword:
                # Sometimes the keyword might not be properly classified
                first_word = query.split()[0].upper()
                if first_word in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE']:
                    query_type = first_word
                break
        
        # Stricter validation: Check for common SQL syntax errors
        query_upper = query.upper()
        
        # Check for invalid identifier patterns (starting with ., only gibberish)
        import re
        
        # Check for identifiers starting with dot (invalid)
        if re.search(r'\.\s*[a-zA-Z]', query):
            # Dot followed by identifier is invalid unless it's table.column
            words = query.split()
            for word in words:
                if word.startswith('.') and len(word) > 1:
                    return SQLValidationResponse(
                        valid=False,
                        query=query,
                        error_message=f"Invalid identifier: '{word}' - identifiers cannot start with '.'"
                    )
        
        # For SELECT queries, must have columns or * after SELECT
        if query_type == 'SELECT':
            # Check if SELECT is immediately followed by FROM (missing columns)
            if 'SELECT' in query_upper and 'FROM' in query_upper:
                select_pos = query_upper.find('SELECT')
                from_pos = query_upper.find('FROM', select_pos)
                between = query[select_pos + 6:from_pos].strip()
                if not between:
                    return SQLValidationResponse(
                        valid=False,
                        query=query,
                        error_message="SELECT statement missing column list or * before FROM"
                    )
            
            # Check if SELECT has valid column specification
            elif 'SELECT' in query_upper:
                select_pos = query_upper.find('SELECT')
                after_select = query[select_pos + 6:].strip()
                
                # Must have something after SELECT
                if not after_select:
                    return SQLValidationResponse(
                        valid=False,
                        query=query,
                        error_message="SELECT statement incomplete - no columns specified"
                    )
                
                # Check if it's not just a number or invalid syntax
                first_token = after_select.split()[0] if after_select.split() else ""
                if first_token and not any([
                    first_token == '*',
                    first_token.replace('_', '').replace('.', '').isalnum(),  # Valid identifier
                    first_token.upper() in ['DISTINCT', 'ALL', 'TOP'],  # Valid keywords
                ]):
                    return SQLValidationResponse(
                        valid=False,
                        query=query,
                        error_message=f"Invalid column specification after SELECT: '{first_token}'"
                    )
        
        # Check for WHERE clause without proper comparison operators
        if 'WHERE' in query_upper:
            where_pos = query_upper.find('WHERE')
            where_clause = query[where_pos + 5:].strip()
            # Should have at least one comparison operator
            has_operator = any(op in where_clause for op in ['=', '>', '<', '!=', '<>', 'LIKE', 'IN', 'BETWEEN', 'IS'])
            if not has_operator and where_clause:
                return SQLValidationResponse(
                    valid=False,
                    query=query,
                    error_message="WHERE clause missing comparison operator"
                )
        
        # Check for multiple values without proper operators (e.g., "id 4 1")
        # Split by whitespace and look for consecutive numbers
        words = query.split()
        for i in range(len(words) - 1):
            try:
                # Try to parse as number
                float(words[i])
                float(words[i + 1])
                # Two consecutive numbers without operator between them
                return SQLValidationResponse(
                    valid=False,
                    query=query,
                    error_message=f"Invalid syntax: consecutive values '{words[i]} {words[i + 1]}' without operator"
                )
            except ValueError:
                continue
        
        # Format the query for better readability
        formatted_query = sqlparse.format(
            query,
            reindent=True,
            keyword_case='upper',
            identifier_case='lower'
        )
        
        # Additional PostgreSQL-specific validation checks
        error_indicators = [
            (';;', 'Multiple statement terminators detected'),
            ('--', None),  # Comments are OK
            ('/*', None),  # Block comments are OK
        ]
        
        # Check for obviously malformed syntax
        if query.count('(') != query.count(')'):
            return SQLValidationResponse(
                valid=False,
                query=query,
                error_message="Unbalanced parentheses in query"
            )
        
        # Check for SQL injection patterns (basic check)
        dangerous_patterns = [
            "'; DROP",
            '"; DROP',
            "' OR '1'='1",
            '" OR "1"="1'
        ]
        
        for pattern in dangerous_patterns:
            if pattern.upper() in query.upper():
                return SQLValidationResponse(
                    valid=False,
                    query=query,
                    error_message=f"Potentially dangerous SQL pattern detected: {pattern}"
                )
        
        return SQLValidationResponse(
            valid=True,
            query=query,
            formatted_query=formatted_query,
            query_type=query_type
        )
        
    except Exception as e:
        return SQLValidationResponse(
            valid=False,
            query=query,
            error_message=f"Query validation error: {str(e)}"
        )
