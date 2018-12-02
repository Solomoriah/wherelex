# wherelex.py
# Copyright 2012 Chris Gonnerman
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer. Redistributions in binary form
# must reproduce the above copyright notice, this list of conditions and the
# following disclaimer in the documentation and/or other materials provided with
# the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
    wherelex.py

    ``outexpr, values = wherelex.interpreter(inexpr)``

    Analyzes a "where clause" expression with a syntax similar to MySQL, but
    simplified.  Includes support for two-letter logical operators such as "gt"
    for greater than, in support of "mental compatibility" with the old filePro
    16 system.

    wherelex.interpreter() only allows identifiers, operators, strings, and
    numbers; any identifier found is back-tick quoted in the output to prevent
    MySQL from interpreting it as a reserved word.  Function calls are
    obviously out of the question with this version.  Strings may be quoted
    with ", ', or |, and the only way to get a quote into a field is to quote
    it with a different quote character.  Note that the pipe | is allowed as a
    quote character to ease the process of automatic quoting, i.e. from a query
    builder; the pipe was chosen as it rarely appears in input text.

    This is not a full parser, just a lexical analyzer and translator.  Thus,
    it is entirely possible that an expression that passes without error will
    still not execute properly in MySQL.  However, the translated expression
    should not allow any sql injection attacks to be performed.

    Usage:
        outexpr, values = wherelex.interpreter(inexpr)

    **inexpr** is the expression provided by the user

    **outexpr** is the sanitized MySQL expression

    **values** is the list of strings and numbers found in inexpr, ready to be
    provided as the second argument to cursor.execute()
"""

import re

identifier = re.compile(r"\w\w*")
operators = "()=!><"
numeric = re.compile(r"\d\d*")
logical = {
    "and": None,
    "or": None,
    "not": None,
    "like": None,
    "null": None,
}
textops = {
    "eq":   "=",
    "ne":   "!=",
    "lt":   "<",
    "le":   "<=",
    "ge":   ">=",
    "gt":   ">",
}
twinops = [ ">=", "<=", "!=", "<>", ]


class AnalyzerError(Exception):
    pass


def interpreter(s, prefix = None):
    s = s.strip()
    expr = []
    values = []
    while s:
        # check for quoted string first
        if s[0] == '"' or s[0] == "'" or s[0] == "|":
            q = s[0]
            fnd = 0
            for i in range(1, len(s)):
                if s[i] == q:
                    # found it!
                    fnd = 1
                    values.append(s[1:i])
                    expr.append("%s")
                    s = s[i+1:]
                    break
            if not fnd:
                raise AnalyzerError("Mismatched quote near '%s'" % s[:20])
        elif s[0] in operators:
            if s[1:2] and s[1:2] in operators and s[0:2] in twinops:
                expr.append(s[0:2])
                s = s[2:]
            else:
                if s[0] == '=':
                    expr.append("=")
                else:
                    expr.append(s[0])
                s = s[1:]
        elif s[0].lower() >= "a" and s[0].lower() <= "z":
            for i in range(len(s)):
                if not identifier.match(s[i]):
                    break
            v = s[:i]
            s = s[i:]
            v = v.lower()
            if v in logical:
                expr.append(v)
            elif v in textops:
                expr.append(textops[v])
            elif prefix:
                expr.append("%s.`%s`" % (prefix, v))
            else:
                expr.append("`%s`" % v)
        elif numeric.match(s[0]) or s[0] == ".":
            for i in range(len(s)):
                if not numeric.match(s[i]) and s[i] != '.':
                    break
            v = s[:i]
            s = s[i:]
            values.append(v)
            expr.append("%s")
        else:
            raise AnalyzerError("Syntax error near '%s'" % s[:20])
        s = s.strip()

    return " ".join(expr), values


if __name__ == "__main__":

    print "good one"
    expression = """
        (taxyear EQ 2012) and (Name LIKE |Frank%|)
    """

    try:
        expr, values = interpreter(expression)
        print expr
        print `values`
    except:
        print "Error detected."

    print "bad one - quote error"
    expression = """
        (taxyear = 2012) and (Name LIKE "Frank%)
    """

    try:
        expr, values = interpreter(expression)
        print expr
        print `values`
    except:
        print "Error detected."

    print "bad one - semicolon"
    expression = """
        (name like 'a%'); select all from accounts
    """

    try:
        expr, values = interpreter(expression)
        print expr
        print `values`
    except:
        print "Error detected."

    print "good parse, but won't work - function call"
    expression = """
        (mydate = sleep(90))
    """

    try:
        expr, values = interpreter(expression)
        print expr
        print `values`
    except:
        print "Error detected."


# end of file.
