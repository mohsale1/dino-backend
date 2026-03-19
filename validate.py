"""
DINO Backend — Pre-deployment Structure Validator
Run: python validate.py
Exit code 0 = all checks passed, safe to build/deploy
Exit code 1 = failures found, do NOT deploy
"""

import os
import sys
import ast
import importlib.util

# ─────────────────────────────────────────────────────────────────────────────
# EXPECTED FILE MANIFEST
# Every file listed here must exist and be non-empty.
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_FILES = [
    # Entry point
    "src/Main.py",

    # Config
    "src/config/__init__.py",
    "src/config/Settings.py",
    "src/config/Database.py",

    # Core
    "src/core/__init__.py",
    "src/core/Dependencies.py",
    "src/core/Exceptions.py",
    "src/core/Initializer.py",
    "src/core/Security.py",

    # Base
    "src/base/__init__.py",
    "src/base/BaseAuth.py",
    "src/base/BaseModel.py",
    "src/base/BaseRepository.py",
    "src/base/BaseRoleCheck.py",
    "src/base/BaseSchema.py",
    "src/base/BaseService.py",
    "src/base/BaseUser.py",

    # Models
    "src/models/__init__.py",
    "src/models/ApplicationUser.py",
    "src/models/Area.py",
    "src/models/Category.py",
    "src/models/Coupon.py",
    "src/models/HomePageInfo.py",
    "src/models/Item.py",
    "src/models/Order.py",
    "src/models/Organization.py",
    "src/models/Permission.py",
    "src/models/Review.py",
    "src/models/Role.py",
    "src/models/SystemUser.py",
    "src/models/Table.py",
    "src/models/Workspace.py",

    # Schemas
    "src/schemas/__init__.py",
    "src/schemas/ApplicationUser.py",
    "src/schemas/Area.py",
    "src/schemas/Auth.py",
    "src/schemas/Category.py",
    "src/schemas/Coupon.py",
    "src/schemas/HomePageInfo.py",
    "src/schemas/Item.py",
    "src/schemas/Order.py",
    "src/schemas/Organization.py",
    "src/schemas/Permission.py",
    "src/schemas/Role.py",
    "src/schemas/SystemUser.py",
    "src/schemas/Table.py",
    "src/schemas/Workspace.py",

    # Repositories
    "src/repositories/__init__.py",
    "src/repositories/AreaRepository.py",
    "src/repositories/CategoryRepository.py",
    "src/repositories/CouponRepository.py",
    "src/repositories/HomePageInfoRepository.py",
    "src/repositories/ItemRepository.py",
    "src/repositories/OrderRepository.py",
    "src/repositories/OrganizationRepository.py",
    "src/repositories/PermissionRepository.py",
    "src/repositories/ReviewRepository.py",
    "src/repositories/RoleRepository.py",
    "src/repositories/TableRepository.py",
    "src/repositories/UserRepository.py",
    "src/repositories/WorkspaceRepository.py",

    # Utils
    "src/utils/__init__.py",
    "src/utils/Helpers.py",
    "src/utils/Validators.py",

    # System — middleware
    "src/system/__init__.py",
    "src/system/middleware/__init__.py",
    "src/system/middleware/RoleCheck.py",

    # System — routes
    "src/system/routes/__init__.py",
    "src/system/routes/Auth.py",
    "src/system/routes/Billing.py",
    "src/system/routes/Dashboard.py",
    "src/system/routes/Permissions.py",
    "src/system/routes/Registration.py",
    "src/system/routes/Roles.py",
    "src/system/routes/Settings.py",
    "src/system/routes/Users.py",
    "src/system/routes/Workspaces.py",

    # System — services
    "src/system/services/__init__.py",
    "src/system/services/Auth.py",
    "src/system/services/Billing.py",
    "src/system/services/Dashboard.py",
    "src/system/services/Permission.py",
    "src/system/services/Role.py",
    "src/system/services/Settings.py",
    "src/system/services/User.py",
    "src/system/services/Workspace.py",

    # Application — middleware
    "src/application/__init__.py",
    "src/application/middleware/__init__.py",
    "src/application/middleware/RoleCheck.py",

    # Application — routes
    "src/application/routes/__init__.py",
    "src/application/routes/Areas.py",
    "src/application/routes/Auth.py",
    "src/application/routes/Categories.py",
    "src/application/routes/Coupons.py",
    "src/application/routes/Dashboard.py",
    "src/application/routes/HomePage.py",
    "src/application/routes/Items.py",
    "src/application/routes/Menu.py",
    "src/application/routes/Orders.py",
    "src/application/routes/Organizations.py",
    "src/application/routes/Reviews.py",
    "src/application/routes/Tables.py",
    "src/application/routes/Users.py",

    # Application — services
    "src/application/services/__init__.py",
    "src/application/services/Area.py",
    "src/application/services/Auth.py",
    "src/application/services/Category.py",
    "src/application/services/Coupon.py",
    "src/application/services/Dashboard.py",
    "src/application/services/HomePage.py",
    "src/application/services/Item.py",
    "src/application/services/Order.py",
    "src/application/services/Organization.py",
    "src/application/services/Review.py",
    "src/application/services/Table.py",
    "src/application/services/User.py",

    # Deployment
    "Dockerfile",
    ".dockerignore",
    "requirements.txt",
]

# ─────────────────────────────────────────────────────────────────────────────
# REQUIRED SYMBOLS
# { "file": ["ClassName", "function_name", ...] }
# Validates that key classes/functions are actually defined in their files.
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_SYMBOLS = {
    "src/config/Settings.py":                  ["Settings"],
    "src/config/Database.py":                  ["initialize_firestore", "get_firestore_client", "close_firestore"],
    "src/core/Security.py":                    ["verify_password", "get_password_hash", "decode_token", "get_current_user_token"],
    "src/core/Initializer.py":                 ["ApplicationInitializer", "initialize_application"],
    "src/core/Dependencies.py":                ["get_current_system_user"],
    "src/base/BaseRepository.py":              ["BaseRepository"],
    "src/base/BaseAuth.py":                    ["BaseAuth"],
    "src/repositories/RoleRepository.py":      ["RoleRepository"],
    "src/repositories/UserRepository.py":      ["UserRepository"],
    "src/repositories/PermissionRepository.py":["PermissionRepository"],
    "src/system/services/Auth.py":             ["SystemAuthService"],
    "src/system/services/Role.py":             ["RoleService"],
    "src/system/services/User.py":             ["SystemUserService"],
    "src/system/services/Workspace.py":        ["WorkspaceService"],
    "src/system/services/Permission.py":       ["PermissionService"],
    "src/system/routes/Auth.py":               ["router"],
    "src/system/routes/Roles.py":              ["router"],
    "src/system/routes/Users.py":              ["router"],
    "src/system/routes/Workspaces.py":         ["router"],
    "src/system/routes/Permissions.py":        ["router"],
    "src/application/services/Auth.py":        ["ApplicationAuthService"],
    "src/application/routes/Auth.py":          ["router"],
    "src/application/routes/Orders.py":        ["router"],
    "src/application/routes/Organizations.py": ["router"],
    "src/Main.py":                             ["app", "lifespan"],
}

# ─────────────────────────────────────────────────────────────────────────────
# DOCKERIGNORE FORBIDDEN PATTERNS
# These patterns must NOT appear in .dockerignore — they caused the last outage.
# ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN_DOCKERIGNORE_PATTERNS = [
    "routes/",
    "services/",
    "src/",
    "*.py",
]

# ─────────────────────────────────────────────────────────────────────────────
# REQUIRED ENV VARS (checked in Settings.py field definitions)
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_SETTINGS_FIELDS = [
    "APP_NAME",
    "APP_VERSION",
    "ENVIRONMENT",
    "SECRET_KEY",
    "FIREBASE_PROJECT_ID",
    "FIREBASE_DATABASE_ID",
    "CORS_ORIGINS",
    "ENABLE_JWT",
    "BUILD_ID",
    "DEPLOYED_AT",
    "SUPERADMIN_EMAIL",
    "SUPERADMIN_PASSWORD",
    "CREATE_DEFAULT_SUPERADMIN",
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

PASS  = "\033[92m  [PASS]\033[0m"
FAIL  = "\033[91m  [FAIL]\033[0m"
WARN  = "\033[93m  [WARN]\033[0m"
TITLE = "\033[96m{}\033[0m"
BOLD  = "\033[1m{}\033[0m"

def section(title: str):
    print()
    print(TITLE.format(f"{'─' * 60}"))
    print(TITLE.format(f"  {title}"))
    print(TITLE.format(f"{'─' * 60}"))

def get_defined_symbols(filepath: str) -> set:
    """Parse a Python file with AST and return all top-level defined names."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
        return names
    except SyntaxError as e:
        return {"__SYNTAX_ERROR__": str(e)}
    except Exception:
        return set()


# ─────────────────────────────────────────────────────────────────────────────
# CHECK FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def check_required_files() -> int:
    section("1. REQUIRED FILES — existence & non-empty")
    failures = 0
    for path in REQUIRED_FILES:
        if not os.path.exists(path):
            print(f"{FAIL} MISSING       {path}")
            failures += 1
        elif os.path.getsize(path) == 0 and not path.endswith("__init__.py"):
            print(f"{FAIL} EMPTY FILE    {path}")
            failures += 1
        else:
            print(f"{PASS} {path}")
    return failures


def check_syntax() -> int:
    section("2. PYTHON SYNTAX — all .py files")
    failures = 0
    py_files = []
    for root, _, files in os.walk("src"):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    py_files.sort()

    for path in py_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source, filename=path)
            print(f"{PASS} {path}")
        except SyntaxError as e:
            print(f"{FAIL} SYNTAX ERROR  {path}  →  line {e.lineno}: {e.msg}")
            failures += 1
    return failures


def check_required_symbols() -> int:
    section("3. REQUIRED SYMBOLS — classes & functions")
    failures = 0
    for filepath, symbols in REQUIRED_SYMBOLS.items():
        if not os.path.exists(filepath):
            print(f"{FAIL} FILE MISSING  {filepath}")
            failures += len(symbols)
            continue

        defined = get_defined_symbols(filepath)

        if "__SYNTAX_ERROR__" in defined:
            print(f"{FAIL} SYNTAX ERROR  {filepath}")
            failures += len(symbols)
            continue

        for symbol in symbols:
            if symbol in defined:
                print(f"{PASS} {filepath}  →  {symbol}")
            else:
                print(f"{FAIL} NOT FOUND    {filepath}  →  {symbol}")
                failures += 1
    return failures


def check_dockerignore() -> int:
    section("4. .dockerignore — forbidden patterns")
    failures = 0
    path = ".dockerignore"
    if not os.path.exists(path):
        print(f"{FAIL} .dockerignore not found")
        return 1

    with open(path, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]

    for pattern in FORBIDDEN_DOCKERIGNORE_PATTERNS:
        if pattern in lines:
            print(f"{FAIL} FORBIDDEN PATTERN in .dockerignore: '{pattern}'  ← this excludes source files from the image")
            failures += 1
        else:
            print(f"{PASS} Pattern '{pattern}' is not excluded")
    return failures


def check_dockerfile() -> int:
    section("5. Dockerfile — required directives")
    failures = 0
    path = "Dockerfile"
    if not os.path.exists(path):
        print(f"{FAIL} Dockerfile not found")
        return 1

    with open(path, "r") as f:
        content = f.read()

    checks = {
        "FROM python:3.11":         "Base image is python:3.11",
        "COPY requirements.txt":    "requirements.txt is copied",
        "COPY . .":                 "Source code is copied",
        "EXPOSE 8080":              "Port 8080 is exposed",
        "uvicorn src.Main:app":     "Correct uvicorn entrypoint",
        "PYTHONDONTWRITEBYTECODE":  "Bytecode writing disabled",
        "PYTHONUNBUFFERED":         "Stdout unbuffered",
        "BUILD_ID":                 "BUILD_ID build arg present",
        "DEPLOYED_AT":              "DEPLOYED_AT build arg present",
    }

    for directive, label in checks.items():
        if directive in content:
            print(f"{PASS} {label}")
        else:
            print(f"{FAIL} MISSING: {label}  (expected '{directive}')")
            failures += 1
    return failures


def check_requirements() -> int:
    section("6. requirements.txt — critical packages")
    failures = 0
    path = "requirements.txt"
    if not os.path.exists(path):
        print(f"{FAIL} requirements.txt not found")
        return 1

    with open(path, "r") as f:
        content = f.read().lower()

    packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "python-jose",
        "bcrypt",
        "firebase-admin",
        "google-cloud-firestore",
        "python-dotenv",
        "email-validator",
        "python-multipart",
    ]

    for pkg in packages:
        if pkg in content:
            print(f"{PASS} {pkg}")
        else:
            print(f"{FAIL} MISSING package: {pkg}")
            failures += 1
    return failures


def check_settings_fields() -> int:
    section("7. Settings — required env var fields")
    failures = 0
    path = "src/config/Settings.py"
    if not os.path.exists(path):
        print(f"{FAIL} Settings.py not found")
        return 1

    with open(path, "r") as f:
        content = f.read()

    for field in REQUIRED_SETTINGS_FIELDS:
        if field in content:
            print(f"{PASS} {field}")
        else:
            print(f"{FAIL} MISSING field: {field}")
            failures += 1
    return failures


def check_no_stale_pycache() -> int:
    section("8. __pycache__ — stale bytecode check")
    warnings = 0
    for root, dirs, files in os.walk("src"):
        if "__pycache__" in root:
            pyc_files = [f for f in files if f.endswith(".pyc")]
            if pyc_files:
                print(f"{WARN} Found {len(pyc_files)} .pyc file(s) in {root}")
                print(f"       Run: find . -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; true")
                warnings += 1
    if warnings == 0:
        print(f"{PASS} No stale __pycache__ directories found")
    return 0  # warnings only, not failures


def check_init_files() -> int:
    section("9. __init__.py — every package has one")
    failures = 0
    for root, dirs, files in os.walk("src"):
        # Skip __pycache__ dirs
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        # src/ itself is not a package — only subdirectories need __init__.py
        if root == "src":
            continue
        if "__init__.py" not in files:
            print(f"{FAIL} MISSING __init__.py in {root}/")
            failures += 1
        else:
            print(f"{PASS} {root}/__init__.py")
    return failures


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print()
    print(BOLD.format("=" * 60))
    print(BOLD.format("  DINO BACKEND — PRE-DEPLOYMENT VALIDATOR"))
    print(BOLD.format("=" * 60))

    total_failures = 0
    total_failures += check_required_files()
    total_failures += check_syntax()
    total_failures += check_required_symbols()
    total_failures += check_dockerignore()
    total_failures += check_dockerfile()
    total_failures += check_requirements()
    total_failures += check_settings_fields()
    total_failures += check_no_stale_pycache()
    total_failures += check_init_files()

    print()
    print(BOLD.format("=" * 60))
    if total_failures == 0:
        print("\033[92m" + BOLD.format("  ALL CHECKS PASSED — safe to build and deploy") + "\033[0m")
    else:
        print("\033[91m" + BOLD.format(f"  {total_failures} CHECK(S) FAILED — fix before deploying") + "\033[0m")
    print(BOLD.format("=" * 60))
    print()

    sys.exit(0 if total_failures == 0 else 1)


if __name__ == "__main__":
    main()
