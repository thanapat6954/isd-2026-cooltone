"""Bound SQL values; materialization is for constraint checks, never execution."""
import math
import re
from .database import SqlValidationError

TOKENS = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^]]*\]|\?\d*|[:@$][A-Za-z_]\w*")


class BoundSQL(str):
    def __new__(cls, sql, parameters=()):
        value = super().__new__(cls, sql)
        value.parameters = parameters
        return value


def constraint_sql(sql, parameters=()):
    markers = [m for m in TOKENS.finditer(sql) if m[0][0] in '?:@$']
    # Quoted identifiers/strings never become parameters.
    if isinstance(parameters, dict):
        if any(m[0].startswith('?') for m in markers) or {m[0][1:] for m in markers} != set(parameters):
            raise SqlValidationError('Named parameter keys must match SQL markers exactly; '
                f'markers={[m[0] for m in markers]!r}, keys={sorted(parameters)!r}')
        values = [parameters[m[0][1:]] for m in markers]
    else:
        if not isinstance(parameters, (list, tuple)) or any(m[0] != '?' for m in markers) or len(markers) != len(parameters):
            raise SqlValidationError('Positional parameters must match SQL markers exactly; '
                f'markers={[m[0] for m in markers]!r}, binding_count={len(parameters) if isinstance(parameters, (list, tuple)) else "invalid"}')
        values = list(parameters)
    def literal(value):
        if value is None:
            return 'NULL'
        if isinstance(value, bool):
            return str(int(value))
        if isinstance(value, (int, float)) and math.isfinite(value):
            return str(value)
        if isinstance(value, str):
            return "'" + value.replace("'", "''") + "'"
        raise SqlValidationError('SQL parameters must be finite scalar values')
    result, start = [], 0
    for marker, value in zip(markers, values):
        result.extend([sql[start:marker.start()], literal(value)])
        start = marker.end()
    return ''.join(result) + sql[start:]
