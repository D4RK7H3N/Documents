import fnmatch
import re

BUILTIN_FORBIDDEN_PATTERNS = [
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "id_rsa*",
    "Dockerfile",
    "Dockerfile.*",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    ".github/workflows/*",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    ".circleci/*",
    "deploy/*",
    "deployment/*",
    "k8s/*",
    "kubernetes/*",
    "helm/*",
    "terraform/*",
    "*.tf",
    "*.tfvars",
    ".kube/*",
    ".aws/*",
]

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_AUTH_RE = re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[^\s,;]+")
_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client_secret)"
    r"(\s*[:=]\s*)(['\"]?)[^\s,;'\"}]+\3"
)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def find_forbidden(paths, extra_patterns=None):
    """Return the changed paths that match a built-in or project-specific rule."""
    patterns = list(BUILTIN_FORBIDDEN_PATTERNS) + [p for p in (extra_patterns or []) if p]
    matched = []
    for raw in paths:
        path = raw.replace("\\", "/").lstrip("./")
        basename = path.rsplit("/", 1)[-1]
        for pattern in patterns:
            pattern = pattern.replace("\\", "/").lstrip("./")
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(basename, pattern):
                matched.append(raw)
                break
    return matched


def redact(text):
    """Strip anything that resembles a credential or personal identifier."""
    if not text:
        return ""
    value = _AUTH_RE.sub(lambda m: m.group(1) + (m.group(2) or "") + "[REDACTED]", text)
    value = _SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + m.group(3) + "[REDACTED]" + m.group(3), value)
    value = _JWT_RE.sub("[REDACTED]", value)
    value = _EMAIL_RE.sub("[EMAIL]", value)
    return value
