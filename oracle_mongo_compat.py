#!/usr/bin/env python3
"""
oracle_mongo_compat.py
======================
Static scanner that flags MongoDB driver code (C#, TypeScript/JavaScript, Python)
and config files that are likely to break when the application is pointed at
Oracle Database API for MongoDB (Oracle JSON / Autonomous JSON Database).

Rules are derived from Oracle's documentation:
  * "Feature Support" reference (Oracle Database API for MongoDB, F44905-26, Aug 2026)
  * "Other Differences Between MongoDB and Oracle Database"

Usage
-----
  python oracle_mongo_compat.py <path> [<path> ...]
        [--target 26ai|19c]          Oracle DB release you will run on (default 26ai)
        [--format text|json|md|sarif] (default text)
        [--output FILE]
        [--min-severity error|warn|info] (default info)
        [--fail-on error|warn|never]  exit code 1 if findings at/above this level (default error)
        [--include-comments]          also scan commented-out lines
        [--exclude-dir NAME ...]      extra directory names to skip

Severity
--------
  ERROR  Will fail (unsupported feature / error raised by Oracle).
  WARN   Preview-only, version-dependent, silently ignored, or high-risk behaviour.
  INFO   Review manually (behavioural differences a static scan can't confirm).

Limitations
-----------
  * Pattern-based, not a full parser: expect some false positives/negatives.
  * C# LINQ (AsQueryable) and ODM layers (Mongoose, EF Core provider, MongoEngine,
    Beanie) generate operators at runtime; those operators are not visible here.
    Run your test suite against Oracle and use explain() to see generated SQL.
  * Field-order dependence, multi-database transactions and data-level issues
    (object _id values, duplicate keys in documents) can only be partly detected.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"
SEV_RANK = {ERROR: 0, WARN: 1, INFO: 2}

# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------
LANG_BY_EXT = {
    ".cs": "cs",
    ".ts": "ts", ".tsx": "ts", ".js": "ts", ".jsx": "ts", ".mjs": "ts", ".cjs": "ts",
    ".py": "py",
    ".json": "cfg", ".yaml": "cfg", ".yml": "cfg", ".env": "cfg", ".config": "cfg",
    ".xml": "cfg", ".ini": "cfg", ".toml": "cfg", ".properties": "cfg",
}
DEFAULT_EXCLUDED_DIRS = {
    "node_modules", ".git", "bin", "obj", "dist", "build", "out", "coverage",
    "venv", ".venv", "env", "__pycache__", "packages", ".idea", ".vs", ".vscode",
    "site-packages", ".next", ".nuxt", ".tox", ".mypy_cache", ".pytest_cache",
}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}


# ---------------------------------------------------------------------------
# Operator / stage tables (from Oracle "Feature Support")
# ---------------------------------------------------------------------------
_LEGACY_GEO = "Legacy coordinate shape not supported; use $geoWithin/$geoIntersects with $geometry (GeoJSON)."
_SERVER_JS = "Server-side JavaScript is not supported."
_NS_EXPR = "Aggregation expression operator not supported."
_NS_STAGE = "Aggregation stage not supported."
_NS_VAR = "System variable not supported."

UNSUPPORTED_OPS = {
    # query / projection
    "$where": _SERVER_JS + " ($where)",
    "$jsonSchema": "$jsonSchema query operator is not supported (validator via collMod is supported on 26ai).",
    "$box": _LEGACY_GEO, "$center": _LEGACY_GEO, "$centerSphere": _LEGACY_GEO,
    "$polygon": _LEGACY_GEO, "$uniqueDocs": _LEGACY_GEO,
    "$meta": "$meta (textScore / searchScore metadata) is not supported.",
    # stages
    "$currentOp": _NS_STAGE, "$geoNear": _NS_STAGE + " Use $near/$nearSphere in find(), or $sql.",
    "$listLocalSessions": _NS_STAGE, "$listSessions": _NS_STAGE,
    "$planCacheStats": _NS_STAGE, "$redact": _NS_STAGE,
    "$setWindowFields": _NS_STAGE + " Use a $sql stage with SQL window functions instead.",
    # expressions
    "$dateFromParts": _NS_EXPR, "$anyElementFalse": _NS_EXPR, "$setEquals": _NS_EXPR,
    "$setIsSubset": _NS_EXPR, "$indexOfBytes": _NS_EXPR, "$regexFind": _NS_EXPR,
    "$regexFindAll": _NS_EXPR, "$strLenBytes": _NS_EXPR, "$strLenCP": _NS_EXPR,
    "$substr": _NS_EXPR + " Use $substrCP.", "$substrBytes": _NS_EXPR + " Use $substrCP.",
    "$sampleRate": _NS_EXPR,
    "$accumulator": _SERVER_JS + " ($accumulator)", "$function": _SERVER_JS + " ($function)",
    "$$DESCEND": _NS_VAR, "$$KEEP": _NS_VAR, "$$PRUNE": _NS_VAR, "$$REMOVE": _NS_VAR,
}

# Not in Oracle's support list at all -> assume unsupported, verify.
NOT_LISTED_OPS = {
    "$densify", "$fill", "$searchMeta", "$median", "$percentile", "$minN",
    "$queryStats", "$toUUID", "$tsIncrement", "$tsSecond", "$shardedDataDistribution",
    "$changeStreamSplitLargeEvent", "$listSampledQueries", "$rankFusion", "$scoreFusion",
}

CONTEXT_OPS = {
    "$firstN": (WARN, "Supported as an array expression but NOT as a $group accumulator."),
    "$lastN": (WARN, "Supported as an array expression but NOT as a $group accumulator."),
    "$maxN": (ERROR, "$maxN accumulator is not supported."),
    "$slice": (INFO, "$slice is NOT supported as a find() projection operator (OK as $push modifier / aggregation expression)."),
}

PREVIEW_OPS = {
    "$changeStream": "Change streams are a PREVIEW feature (26ai); must be enabled (mongo.preview) and may change.",
    "$search": "$search is a PREVIEW feature (26ai); requires preview enablement.",
    "$vectorSearch": "$vectorSearch is a PREVIEW feature (26ai); requires preview enablement ($preview hint).",
    "$listSearchIndexes": "$listSearchIndexes is a PREVIEW feature (26ai).",
}

# Supported only from 26ai -> error when --target 19c
SINCE_26AI_OPS = {
    "$bitsAllSet", "$bitsAnySet", "$bitsAllClear", "$bitsAnyClear", "$expr", "$mod",
    "$addFields", "$bucket", "$bucketAuto", "$documents", "$facet", "$graphLookup",
    "$group", "$indexStats", "$lookup", "$merge", "$out", "$replaceRoot",
    "$replaceWith", "$sample", "$sortByCount", "$unionWith", "$unwind", "$external",
}

OP_TOKEN = re.compile(r"(?<![\w$])(\$\$?[A-Za-z][A-Za-z0-9]*)\b")

# Database commands (passed to runCommand / db.command / new BsonDocument("cmd", ...))
UNSUPPORTED_COMMANDS = [
    "mapReduce", "currentOp", "killOp", "createUser", "dropUser", "updateUser",
    "grantRolesToUser", "revokeRolesFromUser", "usersInfo", "dropAllUsersFromDatabase",
    "createRole", "dropRole", "updateRole", "rolesInfo", "grantRolesToRole",
    "revokePrivilegesFromRole", "dropAllRolesFromDatabase", "shardCollection",
    "enableSharding", "reshardCollection", "convertToCapped", "cloneCollectionAsCapped",
    "parallelCollectionScan", "dbHash", "connPoolStats", "getPrevError", "filemd5", "top",
    "profile",
]
CMD_RE = re.compile(
    r"""(?:["'](%s)["']|(?<![\w.])(%s)\s*:)""" % ("|".join(UNSUPPORTED_COMMANDS), "|".join(UNSUPPORTED_COMMANDS))
)
NOOP_COMMANDS_RE = re.compile(r"""["'](reIndex|setParameter|repairDatabase|compact|getLog)["']""")


# ---------------------------------------------------------------------------
# Language-specific API rules: (langs, regex, severity, rule_id, message, target_only)
#   target_only: None = always, "19c" = only when --target 19c
# ---------------------------------------------------------------------------
R = re.compile
ALL = ("cs", "ts", "py")
API_RULES = [
    # ---- map-reduce
    (("cs",), R(r"\.MapReduce(Async)?\s*[<(]"), ERROR, "MAPREDUCE", "mapReduce is not supported. Rewrite as an aggregation pipeline or $sql.", None),
    (("ts",), R(r"\.mapReduce\s*\("), ERROR, "MAPREDUCE", "mapReduce is not supported. Rewrite as an aggregation pipeline or $sql.", None),
    (("py",), R(r"\.(inline_)?map_reduce\s*\("), ERROR, "MAPREDUCE", "mapReduce is not supported. Rewrite as an aggregation pipeline or $sql.", None),
    # ---- change streams (preview)
    (("cs",), R(r"\.Watch(Async)?\s*[<(]"), WARN, "CHANGE_STREAM", "Change streams are PREVIEW-only on Oracle (26ai) and must be explicitly enabled.", None),
    (("ts", "py"), R(r"\.watch\s*\("), WARN, "CHANGE_STREAM", "Change streams are PREVIEW-only on Oracle (26ai) and must be explicitly enabled. (Ignore if this is not a MongoDB watch().)", None),
    # ---- tailable cursors / capped collections
    (("cs",), R(r"CursorType\.Tailable(Await)?"), ERROR, "TAILABLE", "Tailable cursors require capped collections, which Oracle does not support.", None),
    (("ts",), R(r"\btailable\s*:\s*true|\bawaitData\s*:\s*true"), ERROR, "TAILABLE", "Tailable cursors require capped collections, which Oracle does not support.", None),
    (("py",), R(r"CursorType\.TAILABLE(_AWAIT)?"), ERROR, "TAILABLE", "Tailable cursors require capped collections, which Oracle does not support.", None),
    (("cs",), R(r"\bCapped\s*=\s*true"), ERROR, "CAPPED", "Capped collections are not supported. Use a TTL index (expireAfterSeconds, 26ai) or scheduled cleanup.", None),
    (("ts",), R(r"\bcapped\s*:\s*(true|\{|\d)"), ERROR, "CAPPED", "Capped collections are not supported. Use a TTL index (expireAfterSeconds, 26ai) or scheduled cleanup.", None),
    (("py",), R(r"\bcapped\s*=\s*True|[\"']capped[\"']\s*:\s*True"), ERROR, "CAPPED", "Capped collections are not supported. Use a TTL index (expireAfterSeconds, 26ai) or scheduled cleanup.", None),
    # ---- collation
    (("cs",), R(r"\bCollation\s*=|new\s+Collation\s*\("), ERROR, "COLLATION", "The collation option raises an error on Oracle (Unicode binary ordering is used). Normalise case in data/queries instead.", None),
    (("ts",), R(r"\bcollation\s*:"), ERROR, "COLLATION", "The collation option raises an error on Oracle (Unicode binary ordering is used). Normalise case in data/queries instead.", None),
    (("py",), R(r"\bcollation\s*=|\bCollation\s*\("), ERROR, "COLLATION", "The collation option raises an error on Oracle (Unicode binary ordering is used). Normalise case in data/queries instead.", None),
    # ---- retryable writes set in code
    (("cs",), R(r"\bRetryWrites\s*=\s*true"), ERROR, "RETRY_WRITES", "Retryable writes raise an error on Oracle. Set RetryWrites = false.", None),
    (("ts",), R(r"\bretryWrites\s*:\s*true"), ERROR, "RETRY_WRITES", "Retryable writes raise an error on Oracle. Set retryWrites: false.", None),
    (("py",), R(r"\bretry[Ww]rites\s*=\s*True"), ERROR, "RETRY_WRITES", "Retryable writes raise an error on Oracle. Set retryWrites=False.", None),
    # ---- authentication
    (ALL, R(r"SCRAM-SHA-(1|256)|MONGODB-X509|MONGODB-AWS|MONGODB-OIDC|GSSAPI|\bScramSha(1|256)\b"), ERROR, "AUTH_MECH", "Only PLAIN authentication (authSource=$external) is supported by Oracle.", None),
    (("cs",), R(r"MongoCredential\.CreateCredential\s*\("), WARN, "AUTH_MECH", "CreateCredential negotiates SCRAM. Oracle needs PLAIN: MongoCredential.CreatePlainCredential(\"$external\", user, password).", None),
    # ---- index types & options
    (("cs",), R(r"IndexKeys\.(Geo2DSphere|Geo2D|GeoHaystack|Hashed)\b"), ERROR, "INDEX_TYPE", "2d / 2dsphere / hashed indexes are not supported. For GeoJSON create an Oracle spatial index via SQL.", None),
    (("ts",), R(r"[:,]\s*[\"'](2d|2dsphere|hashed|geoHaystack)[\"']"), ERROR, "INDEX_TYPE", "2d / 2dsphere / hashed indexes are not supported. For GeoJSON create an Oracle spatial index via SQL.", None),
    (("py",), R(r"\b(pymongo\.)?(GEO2D|GEOSPHERE|GEOHAYSTACK|HASHED)\b|[:,]\s*[\"'](2d|2dsphere|hashed)[\"']"), ERROR, "INDEX_TYPE", "2d / 2dsphere / hashed indexes are not supported. For GeoJSON create an Oracle spatial index via SQL.", None),
    (ALL, R(r"\b[Pp]artialFilterExpression\b|partial_filter_expression"), ERROR, "INDEX_OPTION", "partialFilterExpression is not supported on Oracle indexes.", None),
    (("cs",), R(r"\bHidden\s*=\s*true"), ERROR, "INDEX_OPTION", "Hidden indexes are not supported.", None),
    (("ts",), R(r"\bhidden\s*:\s*true"), WARN, "INDEX_OPTION", "Hidden indexes are not supported (ignore if not an index option).", None),
    (("py",), R(r"\bhidden\s*=\s*True|[\"']hidden[\"']\s*:\s*True"), WARN, "INDEX_OPTION", "Hidden indexes are not supported (ignore if not an index option).", None),
    (ALL, R(r"\b[Ss]torageEngine\b|storage_engine"), ERROR, "INDEX_OPTION", "storageEngine options are not supported.", None),
    (ALL, R(r"\b[Ee]xpireAfter(Seconds)?\b|expire_after_seconds"), ERROR, "INDEX_19C", "TTL indexes (expireAfterSeconds) are supported only from Oracle 26ai.", "19c"),
    # ---- C# typed builders that map to unsupported stages/operators
    (("cs",), R(r"\.(SetWindowFields|GeoNear|Redact)\s*[<(]"), ERROR, "STAGE", "This aggregation stage ($setWindowFields / $geoNear / $redact) is not supported.", None),
    (("cs",), R(r"Projection\.(Slice|Meta\w*)\s*\(|\.MetaTextScore\s*\(|\.MetaSearch\w*\s*\("), ERROR, "PROJECTION", "Projection $slice / $meta is not supported by Oracle's find().", None),
    (("cs",), R(r"Filter\.(GeoWithinBox|GeoWithinCenter|GeoWithinCenterSphere|GeoWithinPolygon)\s*\("), ERROR, "GEO_LEGACY", _LEGACY_GEO, None),
    (("cs",), R(r"Filter\.JsonSchema\s*\("), ERROR, "JSON_SCHEMA", "$jsonSchema query operator is not supported.", None),
    (("cs",), R(r"\.AsQueryable\s*\("), INFO, "LINQ", "LINQ is translated to MQL at runtime; operators it generates are not visible to this scan. Verify with explain() against Oracle.", None),
    # ---- unsupported BSON types
    (("cs",), R(r"\bBson(JavaScript|JavaScriptWithScope|Symbol|Undefined)\b"), ERROR, "BSON_TYPE", "This BSON type is not supported by Oracle (JavaScript / Symbol / Undefined).", None),
    (("cs",), R(r"\bBson(Timestamp|MinKey|MaxKey|RegularExpression)\b"), WARN, "BSON_TYPE", "Timestamp / MinKey / MaxKey / Regex BSON types can't be stored in Oracle documents (converted to string on load). Fine only as a query value where supported.", None),
    (("ts",), R(r"\bnew\s+(Code|BSONSymbol)\s*\(|\bBSONSymbol\b"), ERROR, "BSON_TYPE", "This BSON type is not supported by Oracle (Code / Symbol).", None),
    (("ts",), R(r"\bnew\s+(Timestamp|MinKey|MaxKey|BSONRegExp)\s*\("), WARN, "BSON_TYPE", "Timestamp / MinKey / MaxKey / BSONRegExp can't be stored in Oracle documents.", None),
    (("py",), R(r"from\s+bson(\.\w+)?\s+import[^\n#]*\b(Code|Symbol)\b|\bbson\.code\b"), ERROR, "BSON_TYPE", "bson Code (JavaScript) type is not supported by Oracle.", None),
    (("py",), R(r"from\s+bson(\.\w+)?\s+import[^\n#]*\b(Timestamp|MinKey|MaxKey|Regex)\b|\bbson\.(timestamp|min_key|max_key|regex)\b"), WARN, "BSON_TYPE", "Timestamp / MinKey / MaxKey / Regex BSON types can't be stored in Oracle documents.", None),
    (ALL, R(r"\bDecimal128\b"), INFO, "DECIMAL128", "Decimal128 is converted to Oracle NUMBER; the conversion can be lossy. Check precision-sensitive values.", None),
    # ---- object-valued _id
    (("ts", "py"), R(r"""["']?\b_id\b["']?\s*:\s*\{(?!\s*["']?\$|\s*\}|\s*["']?(type|required|auto|default)\b)"""), WARN, "ID_OBJECT", "Object-valued _id is not supported (only ObjectId, string, numbers, UUID binary). Ignore if this is a query sub-document.", None),
    (("cs",), R(r"""["']_id["']\s*,\s*new\s+BsonDocument\s*(\(\s*"(?!\$)|\{\s*\{\s*"(?!\$))"""), WARN, "ID_OBJECT", "Object-valued _id is not supported (only ObjectId, string, numbers, UUID binary).", None),
    # ---- field-order dependence
    (("ts",), R(r"Object\.(keys|entries|values)\([^)]*\)\s*\[\s*0\s*\]|JSON\.stringify\([^)]*\)\s*[!=]==?"), INFO, "FIELD_ORDER", "Oracle does not preserve field order in documents. Don't rely on first key / serialized-string equality.", None),
    (("py",), R(r"list\([^)]*\.(keys|items|values)\(\)\)\s*\[\s*0\s*\]|json\.dumps\([^)]*\)\s*[!=]="), INFO, "FIELD_ORDER", "Oracle does not preserve field order in documents. Don't rely on first key / serialized-string equality.", None),
    (("cs",), R(r"\.GetElement\s*\(\s*0\s*\)|\.Elements\.First\s*\(|\.Names\.First\s*\(|\.ToJson\(\)\s*==|\[\s*0\s*\]\.Name\b"), INFO, "FIELD_ORDER", "Oracle does not preserve field order in documents. Don't rely on element position / serialized-string equality.", None),
    # ---- read/write concern & read preference
    (ALL, R(r"\b([Rr]ead|[Ww]rite)_?[Cc]oncern\b|\bw\s*[:=]\s*[\"']majority[\"']"), INFO, "CONCERN", "Read/write concerns do not apply on Oracle (ACID, read-committed). Behaviour relying on them should be reviewed.", None),
    # ---- 19c-only limitations
    (("cs",), R(r"\.Aggregate(Async)?\s*[<(]|\.AsQueryable\s*\("), ERROR, "AGG_19C", "Most aggregation pipelines (and LINQ) are not supported on Oracle 19c; aggregate is supported from 26ai. Rewrite with $sql or upgrade.", "19c"),
    (("ts", "py"), R(r"\.aggregate\s*\("), ERROR, "AGG_19C", "Most aggregation pipelines are not supported on Oracle 19c; aggregate is supported from 26ai. Rewrite with $sql or upgrade.", "19c"),
    (ALL, R(r"\.(createIndex|createIndexes|ensureIndex|create_index|create_indexes|CreateOne(Async)?|CreateMany(Async)?)\s*[<(]"), WARN, "INDEX_19C", "createIndexes is a no-op on 19c (index silently NOT created). Create indexes with SQL / Database Actions.", "19c"),
]

# ---- file-level rule patterns
TXN_RE = {
    "cs": R(r"\b(StartTransaction|WithTransaction)(Async)?\b"),
    "ts": R(r"\b(startTransaction|withTransaction)\b"),
    "py": R(r"\b(start_transaction|with_transaction)\b"),
}
DDL_RE = {
    "cs": R(r"\b(CreateCollection(Async)?|Indexes\.Create(One|Many)(Async)?|DropCollection(Async)?|CreateView(Async)?)\b"),
    "ts": R(r"\b(createCollection|createIndex|createIndexes|dropCollection|createView|syncIndexes|ensureIndexes)\b"),
    "py": R(r"\b(create_collection|create_index|create_indexes|drop_collection)\b"),
}
LOOKUP_RE = R(r"""["']?\$lookup["']?""")
LET_RE = R(r"""["']?\blet\b["']?\s*[:=]|["']let["']\s*,""")
INDEX_NAME_RE = {
    "cs": R(r"\bName\s*=\s*\"([^\"]+)\""),
    "ts": R(r"\bname\s*:\s*[\"']([^\"']+)[\"']"),
    "py": R(r"\bname\s*=\s*[\"']([^\"']+)[\"']"),
}
INDEX_CALL_RE = R(r"(createIndex|create_index|CreateIndexOptions|CreateIndexModel|IndexOptions|ensureIndex|\.index\s*\()")

URI_RE = R(r"mongodb(\+srv)?://[^\s\"'`<>;,)]+(?:[;,][^\s\"'`<>)]*)?")
# settings that may be supplied outside the URI (kwargs / options objects)
OUT_OF_URI = {
    "retryWrites": R(r"retry[Ww]rites\s*[:=]\s*(false|False)|RetryWrites\s*=\s*false"),
    "loadBalanced": R(r"load[Bb]alanced\s*[:=]\s*(true|True)|LoadBalanced\s*=\s*true"),
    "authMechanism": R(r"auth[Mm]echanism\s*[:=]\s*[\"']PLAIN[\"']|CreatePlainCredential|[\"']PLAIN[\"']"),
}


@dataclass
class Finding:
    file: str
    line: int
    col: int
    severity: str
    rule: str
    message: str
    snippet: str


def is_comment(line: str, lang: str) -> bool:
    s = line.lstrip()
    if lang == "py":
        return s.startswith("#")
    if lang in ("cs", "ts"):
        return s.startswith("//") or s.startswith("*") or s.startswith("/*")
    if lang == "cfg":
        return s.startswith("#") or s.startswith(";")
    return False


def check_uri(uri: str, file_text: str):
    """Yield (severity, rule, message) for a MongoDB connection string."""
    out = []
    low = uri.lower()
    params = {}
    if "?" in uri:
        for kv in re.split(r"[&;]", uri.split("?", 1)[1]):
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k.strip().lower()] = v.strip()

    code_only = URI_RE.sub("", file_text)

    def elsewhere(key):
        return bool(OUT_OF_URI[key].search(code_only))

    if low.startswith("mongodb+srv://"):
        out.append((WARN, "URI_SRV", "mongodb+srv:// (SRV lookup) is not used by Oracle endpoints; use mongodb://host:27017/..."))
    if params.get("retrywrites", "").lower() != "false":
        sev = INFO if ("retrywrites" not in params and elsewhere("retryWrites")) else ERROR
        out.append((sev, "URI_RETRY_WRITES", "retryWrites=false is required (drivers default to true; retryable writes raise an error on Oracle)."
                    + (" Appears to be set in code - verify." if sev == INFO else "")))
    if params.get("loadbalanced", "").lower() != "true":
        sev = INFO if ("loadbalanced" not in params and elsewhere("loadBalanced")) else ERROR
        out.append((sev, "URI_LOAD_BALANCED", "loadBalanced=true is required by Oracle Database API for MongoDB."
                    + (" Appears to be set in code - verify." if sev == INFO else "")))
    mech = params.get("authmechanism", "")
    if mech.upper() != "PLAIN":
        sev = INFO if (not mech and elsewhere("authMechanism")) else ERROR
        out.append((sev, "URI_AUTH", "authMechanism=PLAIN&authSource=$external is required (SCRAM/X509/etc. not supported)."
                    + (f" Found authMechanism={mech}." if mech else "")))
    src = params.get("authsource", "")
    if mech.upper() == "PLAIN" and src not in ("$external", "%24external"):
        out.append((WARN, "URI_AUTH_SOURCE", "authSource=$external is expected with PLAIN authentication."))
    if params.get("tls", params.get("ssl", "")).lower() not in ("true",):
        out.append((INFO, "URI_TLS", "Oracle endpoints normally require tls=true (ssl=true)."))
    if "replicaset" in params:
        out.append((WARN, "URI_REPLSET", "replicaSet is not applicable to Oracle and conflicts with loadBalanced=true."))
    if "directconnection" in params:
        out.append((WARN, "URI_DIRECT", "directConnection cannot be combined with loadBalanced=true."))
    return out


def scan_file(path: str, target: str, include_comments: bool, index_names: dict) -> list:
    ext = os.path.splitext(path)[1].lower()
    base = os.path.basename(path)
    lang = LANG_BY_EXT.get(ext)
    if base.startswith(".env"):
        lang = "cfg"
    if not lang or base in SKIP_FILES or base.endswith(".min.js"):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    if len(text) > 5_000_000:
        return []

    findings: list[Finding] = []
    seen = set()
    lines = text.splitlines()

    def add(ln, col, sev, rule, msg):
        key = (ln, rule, msg)
        if key in seen:
            return
        seen.add(key)
        findings.append(Finding(path, ln, col, sev, rule, msg, lines[ln - 1].strip()[:200]))

    for i, line in enumerate(lines, start=1):
        if not include_comments and is_comment(line, lang):
            continue

        # --- connection strings (all file types)
        uri_on_line = False
        for m in URI_RE.finditer(line):
            uri_on_line = True
            for sev, rule, msg in check_uri(m.group(0), text):
                add(i, m.start() + 1, sev, rule, msg)

        # --- $operators (skip auth lines like authSource=$external)
        if not uri_on_line and "authSource" not in line and "authsource" not in line:
            for m in OP_TOKEN.finditer(line):
                op = m.group(1)
                col = m.start() + 1
                if op in UNSUPPORTED_OPS:
                    add(i, col, ERROR, "OPERATOR", f"{op}: {UNSUPPORTED_OPS[op]}")
                elif op in PREVIEW_OPS:
                    add(i, col, WARN, "PREVIEW", f"{op}: {PREVIEW_OPS[op]}")
                elif op in CONTEXT_OPS:
                    sev, msg = CONTEXT_OPS[op]
                    add(i, col, sev, "OPERATOR_CONTEXT", f"{op}: {msg}")
                elif op in NOT_LISTED_OPS:
                    add(i, col, WARN, "OPERATOR_UNLISTED", f"{op}: not listed in Oracle's Feature Support table - assume unsupported and test.")
                elif target == "19c" and op in SINCE_26AI_OPS:
                    add(i, col, ERROR, "OPERATOR_19C", f"{op}: supported only from Oracle 26ai.")

        if lang == "cfg":
            continue

        # --- database commands by name
        for m in CMD_RE.finditer(line):
            name = m.group(1) or m.group(2)
            if name in ("top", "profile") and not re.search(r"command|Command|RunCommand|run_command", line):
                continue
            add(i, m.start() + 1, ERROR, "COMMAND", f"Database command '{name}' is not supported by Oracle.")
        m = NOOP_COMMANDS_RE.search(line)
        if m and re.search(r"command|Command", line):
            add(i, m.start() + 1, WARN, "COMMAND_NOOP", f"Command '{m.group(1)}' is a silent no-op on Oracle.")

        # --- language API rules
        for langs, rx, sev, rule, msg, only in API_RULES:
            if lang not in langs or (only and only != target):
                continue
            if lang == "py" and rule == "INDEX_TYPE" and re.match(r"\s*(from|import)\s", line):
                continue
            m = rx.search(line)
            if m:
                add(i, m.start() + 1, sev, rule, msg)

        # --- collect index names for cross-file duplicate check
        if INDEX_CALL_RE.search(line) or (i > 1 and INDEX_CALL_RE.search(lines[i - 2])):
            nm = INDEX_NAME_RE[lang].search(line)
            if nm:
                index_names.setdefault(nm.group(1), []).append((path, i, line.strip()[:200]))

    if lang in ("cs", "ts", "py"):
        # --- $lookup with 'let' (multi-line window)
        for m in LOOKUP_RE.finditer(text):
            window = text[m.end(): m.end() + 600]
            nxt = re.search(r"\$(match|project|group|sort|unwind|limit|skip)\b", window)
            if nxt:
                window = window[: nxt.start()]
            lm = LET_RE.search(window)
            if lm:
                ln = text.count("\n", 0, m.end() + lm.start()) + 1
                add(ln, 1, ERROR, "LOOKUP_LET", "$lookup with 'let' is not supported by Oracle. Use localField/foreignField, or $sql.")
        # C# typed Lookup with let:
        if lang == "cs":
            for m in re.finditer(r"\.Lookup\s*\([^;]{0,400}?\blet\s*:", text, re.S):
                ln = text.count("\n", 0, m.start()) + 1
                add(ln, 1, ERROR, "LOOKUP_LET", "$lookup with 'let' is not supported by Oracle. Use localField/foreignField, or $sql.")

        # --- DDL inside transactions (file-level heuristic)
        tm = TXN_RE[lang].search(text)
        if tm:
            for m in DDL_RE[lang].finditer(text, tm.start()):
                ln = text.count("\n", 0, m.start()) + 1
                if not include_comments and is_comment(lines[ln - 1], lang):
                    continue
                add(ln, 1, WARN, "TXN_DDL", "This file uses transactions and DDL. Creating/dropping collections or indexes inside a transaction raises an error on Oracle; transactions also cannot span databases.")

    return findings


def iter_files(paths, excluded_dirs):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for f in files:
                yield os.path.join(root, f)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def render_text(findings, stats):
    out = []
    by_file = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)
    for file in sorted(by_file):
        out.append(f"\n{file}")
        for f in sorted(by_file[file], key=lambda x: (x.line, SEV_RANK[x.severity])):
            out.append(f"  {f.line}:{f.col}  {f.severity:<5}  {f.rule:<18} {f.message}")
            out.append(f"        > {f.snippet}")
    out.append("\n" + summary_line(stats))
    return "\n".join(out)


def summary_line(stats):
    return (f"Scanned {stats['files']} files (target Oracle {stats['target']}): "
            f"{stats[ERROR]} errors, {stats[WARN]} warnings, {stats[INFO]} info.")


def render_md(findings, stats):
    out = ["# Oracle MongoDB API compatibility report", "", summary_line(stats), ""]
    rules = {}
    for f in findings:
        rules.setdefault((f.severity, f.rule), 0)
        rules[(f.severity, f.rule)] += 1
    out += ["## Summary by rule", "", "| Severity | Rule | Count |", "|---|---|---|"]
    for (sev, rule), n in sorted(rules.items(), key=lambda x: (SEV_RANK[x[0][0]], -x[1])):
        out.append(f"| {sev} | {rule} | {n} |")
    out += ["", "## Findings", "", "| Severity | Location | Rule | Message |", "|---|---|---|---|"]
    for f in sorted(findings, key=lambda x: (SEV_RANK[x.severity], x.file, x.line)):
        msg = f.message.replace("|", "\\|")
        out.append(f"| {f.severity} | `{f.file}:{f.line}` | {f.rule} | {msg} |")
    return "\n".join(out) + "\n"


def render_sarif(findings):
    level = {ERROR: "error", WARN: "warning", INFO: "note"}
    rule_ids = sorted({f.rule for f in findings})
    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "oracle-mongo-compat",
                "informationUri": "https://docs.oracle.com/en/database/oracle/mongodb-api/mgapi/support-mongodb-apis-operations-and-data-types-reference.html",
                "rules": [{"id": r, "shortDescription": {"text": r}} for r in rule_ids],
            }},
            "results": [{
                "ruleId": f.rule,
                "level": level[f.severity],
                "message": {"text": f.message},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": f.file.replace(os.sep, "/")},
                    "region": {"startLine": f.line, "startColumn": f.col},
                }}],
            } for f in findings],
        }],
    }, indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find MongoDB driver code that breaks on Oracle Database API for MongoDB.")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--target", choices=["26ai", "19c"], default="26ai")
    ap.add_argument("--format", choices=["text", "json", "md", "sarif"], default="text")
    ap.add_argument("--output")
    ap.add_argument("--min-severity", choices=["error", "warn", "info"], default="info")
    ap.add_argument("--fail-on", choices=["error", "warn", "never"], default="error")
    ap.add_argument("--include-comments", action="store_true")
    ap.add_argument("--exclude-dir", nargs="*", default=[])
    a = ap.parse_args(argv)

    excluded = DEFAULT_EXCLUDED_DIRS | set(a.exclude_dir)
    findings, index_names, nfiles = [], {}, 0
    for path in iter_files(a.paths, excluded):
        if os.path.splitext(path)[1].lower() in LANG_BY_EXT or os.path.basename(path).startswith(".env"):
            nfiles += 1
        findings += scan_file(path, a.target, a.include_comments, index_names)

    for name, locs in index_names.items():
        if len(locs) > 1:
            for file, ln, snip in locs:
                findings.append(Finding(file, ln, 1, WARN, "INDEX_NAME_DUP",
                                        f"Index name '{name}' is used {len(locs)} times. Oracle index names must be unique per schema (across all collections).", snip))

    min_rank = SEV_RANK[a.min_severity.upper()]
    findings = [f for f in findings if SEV_RANK[f.severity] <= min_rank]
    stats = {"files": nfiles, "target": a.target, ERROR: 0, WARN: 0, INFO: 0}
    for f in findings:
        stats[f.severity] += 1

    if a.format == "json":
        body = json.dumps({"summary": stats, "findings": [asdict(f) for f in findings]}, indent=2)
    elif a.format == "md":
        body = render_md(findings, stats)
    elif a.format == "sarif":
        body = render_sarif(findings)
    else:
        body = render_text(findings, stats)

    if a.output:
        with open(a.output, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(summary_line(stats))
    else:
        print(body)

    if a.fail_on == "never":
        return 0
    limit = SEV_RANK[a.fail_on.upper()]
    return 1 if any(SEV_RANK[f.severity] <= limit for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
