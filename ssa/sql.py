import re

keywords = re.compile(r'([A-Z_]+)  \b  .*?  [\r\n]', re.VERBOSE).findall(
#
# copy-pasted from https://docs.oracle.com/database/121/SQLRF/ap_keywd001.htm#SQLRF55621
#
"""
ACCESS
ADD
ALL *
ALTER *
AND *
ANY *
AS *
ASC
AUDIT
BETWEEN *
BY *
CHAR *
CHECK *
CLUSTER
COLUMN *
COLUMN_VALUE (See Note 1 at the end of this list)
COMMENT
COMPRESS
CONNECT *
CREATE *
CURRENT *
DATE *
DECIMAL *
DEFAULT *
DELETE *
DESC
DISTINCT *
DROP *
ELSE *
EXCLUSIVE
EXISTS *
FILE
FLOAT *
FOR *
FROM *
GRANT *
GROUP *
HAVING *
IDENTIFIED
IMMEDIATE
IN *
INCREMENT
INDEX
INITIAL
INSERT *
INTEGER *
INTERSECT *
INTO *
IS *
LEVEL
LIKE *
LOCK
LONG
MAXEXTENTS
MINUS
MLSLABEL
MODE
MODIFY
NESTED_TABLE_ID (See Note 1 at the end of this list)
NOAUDIT
NOCOMPRESS
NOT *
NOWAIT
NULL *
NUMBER
OF *
OFFLINE
ON *
ONLINE
OPTION
OR *
ORDER *
PCTFREE
PRIOR
PUBLIC
RAW
RENAME
RESOURCE
REVOKE *
ROW *
ROWID (See Note 2 at the end of this list)
ROWNUM
ROWS *
SELECT *
SESSION
SET *
SHARE
SIZE
SMALLINT *
START *
SUCCESSFUL
SYNONYM
SYSDATE
TABLE *
THEN *
TO *
TRIGGER *
UID
UNION *
UNIQUE *
UPDATE *
USER *
VALIDATE
VALUES *
VARCHAR *
VARCHAR2
VIEW
WHENEVER *
WHERE *
WITH *

select *
delete *
update *
insert *

Select *
Delete *
Update *
Insert *
""")

excludes = [
r'%s' % re.escape('size='),
r'%s\b' % re.escape('<input'),
r'%s\b' % re.escape('<option'),
r'^ ( null | NULL ) $'
]

#
# TODO: clean this function up.
#
def keyword_matcher(case_sensitive=True):
    kws = list(keywords)
    if not case_sensitive:
        for kw in keywords:
            kw = kw.lower()
            # only match lowercase keywords whose length is > 3.
            # Otherwise too many false positives.
            if len(kw) <= 3:
                continue
            kws.append(kw.lower())
    fmt = ' | '.join(['(?: %s )' % re.escape(x) for x in kws])
    fmt = r'\b (%s) \b' % fmt
    # filter out HTML.
    fmt = r'(?<! < ) ' + fmt
    fmt = r'(?<! / ) ' + fmt
    return re.compile(fmt, re.VERBOSE)

def word_excluder():
    fmt = r'( %s )' % (' | '.join(['(?: %s )' % x for x in excludes]))
    return re.compile(fmt, re.VERBOSE)

_matcher = keyword_matcher(case_sensitive=True)
_excluder = word_excluder()

def findall(val):
    kws = []
    for line in val.splitlines():
        line = line.strip()
        # skip empty lines.
        if len(line) <= 0:
            continue
        # if the line contains any terms in excluder, skip it.
        if _excluder.search(line):
            continue
        kws += _matcher.findall(line)
    return kws

def is_sql_statement(val):
    kws = findall(val)
    if len(kws) <= 0:
        return False
    word = kws[0].upper()
    return word in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'DROP', 'CREATE', 'USE', 'SHOW']



