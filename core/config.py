# =========================
# Sequoia Core Configuration
# =========================


# ----- Execution limits -----

MAX_STEPS = None
TOOL_TIMEOUT = None
MAX_RETRIES = None
MAX_PARALLEL_TOOLS = None


# ----- Resource management -----

CLOUD_OFFLOAD = True
RESOURCE_AWARE = True

RESOURCE_POLICY = "adaptive"

AUTO_CLOUD_OFFLOAD = True

CPU_POLICY = "adaptive"
AUTO_CPU_THROTTLE = True

THERMAL_POLICY = "adaptive"
AUTO_THERMAL_OFFLOAD = True

BATTERY_POLICY = "adaptive"
AUTO_POWER_SAVING = True
AUTO_CLOUD_OFFLOAD_ON_LOW_BATTERY = True

NETWORK_POLICY = "adaptive"
AUTO_NETWORK_OFFLOAD = True


# ----- Execution target -----

EXECUTION_TARGET = "auto"

AUTO_WORKER_SELECTION = True
AUTO_FAILOVER = True

AUTO_TASK_DECOMPOSITION = True
AUTO_PARALLEL_EXECUTION = True

PARALLELISM_POLICY = "adaptive"
MAX_PARALLEL_BRANCHES = None


# ----- Planning / recovery -----

AUTO_REPLAN = True
REPLAN_POLICY = "adaptive"

MAX_REPLANS = None
AUTO_RECOVERY = True

VERIFY_EACH_STEP = True
AUTO_CORRECT_PLAN = True

ON_VERIFICATION_FAILURE = "replan"
REUSE_FAILED_PATH = False


# ----- Tool selection -----

TOOL_SELECTION_POLICY = "ranked_exhaustive"

TRY_ALL_RELEVANT_TOOLS = True
COMPARE_TOOL_RESULTS = True
STOP_ON_FIRST_SUCCESS = False

TOOL_RANKING_POLICY = "accuracy_utility"

TOOL_SCORE_WEIGHTS = {
    "accuracy": 0.60,
    "utility": 0.30,
    "reliability": 0.10,
}


# ----- Independent verification -----

INDEPENDENT_VERIFICATION = True

VERIFICATION_TOOLS_MIN = 2
REQUIRE_RESULT_AGREEMENT = True

ON_DISAGREEMENT = "replan"


# ----- Model routing -----

MODEL_SELECTION_POLICY = "adaptive"

AUTO_MODEL_ROUTING = True
USE_SPECIALIZED_MODELS = True

COMPARE_MODEL_RESULTS = True
MODEL_FAILOVER = True

JUDGE_MODEL_ENABLED = True
JUDGE_MODEL_POLICY = "on_disagreement"

JUDGE_MODEL_REQUIRED = False
FALLBACK_TO_EVIDENCE_SCORING = True


# ----- Memory -----

MEMORY_POLICY = "adaptive_hybrid"

USE_SEMANTIC_MEMORY = True
USE_EPISODIC_MEMORY = True
USE_FACT_MEMORY = True
USE_RELATIONSHIP_MEMORY = True
USE_TASK_MEMORY = True
USE_CONVERSATION_HISTORY = True

AUTO_MEMORY_RETRIEVAL = True
CROSS_MEMORY_SEARCH = True

RERANK_RETRIEVED_MEMORIES = True
DEDUPLICATE_MEMORIES = True

MEMORY_SELECTION_POLICY = "relevance_accuracy_utility"

MEMORY_CONTEXT_LIMIT = None

AUTO_MEMORY_CONSOLIDATION = True
AUTO_MEMORY_UPDATE = True

CONFLICT_RESOLUTION = "evidence_weighted"


# ----- Permissions -----

PERMISSION_POLICY = "adaptive_capability"

AUTO_EXECUTE_LOW_RISK = True
AUTO_EXECUTE_OWNER_DEVICE = True

REQUIRE_TARGET_AUTHORIZATION = True
REQUIRE_CONFIRMATION_HIGH_IMPACT = True

DEFAULT_UNKNOWN_TOOL_ACTION = "deny"

CAPABILITY_ISOLATION = True
AUDIT_EVERY_TOOL_CALL = True


# ----- Root on owner's Android device -----

ROOT_EXECUTION_POLICY = "auto_owner_device"

AUTO_ROOT_EXECUTION = True
REQUIRE_OWNER_DEVICE = True

VERIFY_ROOT_AVAILABLE = True
AUTO_RECOVER_ROOT_FAILURE = True

CONFIRM_DESTRUCTIVE_ROOT_ACTIONS = True
AUDIT_ROOT_COMMANDS = True


# ----- Android application control -----

APP_CONTROL_POLICY = "auto_owner_device"

AUTO_APP_LAUNCH = True
AUTO_APP_STOP = True
AUTO_APP_RESTART = True

AUTO_APP_STATE_READ = True
AUTO_APP_FILE_OPERATIONS = True
AUTO_APP_PERMISSION_ACTIONS = True

PROTECT_CREDENTIAL_DATA = True
AUDIT_APP_ACTIONS = True


# ----- UI automation -----

AUTO_UI_AUTOMATION = False
ACCESSIBILITY_CONTROL = False
AUTO_SCREEN_INTERACTION = False


# ----- Network / Web -----

NETWORK_ACCESS_POLICY = "auto_authorized"

AUTO_HTTP_REQUESTS = True
AUTO_API_CALLS = True
AUTO_WEB_RESEARCH = True
AUTO_BROWSER_TASKS = True

ALLOW_EXTERNAL_NETWORK = True

AUTO_RETRY_NETWORK_ERRORS = True
AUTO_FAILOVER_NETWORK_ROUTE = True

REQUIRE_AUTHORIZED_TARGETS = True

AUDIT_NETWORK_ACTIONS = True


# ----- Authorized accounts -----

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


# =========================================================
# SETTINGS
# =========================================================

class AccessPolicy(Enum):
    OWNER_ONLY = "owner_only"

    OWNER_AND_AUTHORIZED = (
        "owner_and_authorized_accounts"
    )

    ALL_AUTHORIZED = "all_authorized_accounts"


ACCOUNT_ACCESS_POLICY = AccessPolicy.ALL_AUTHORIZED

# "*" = جميع الحسابات ذات التفويض الصالح
AUTHORIZED_ACCOUNTS = "*"

AUTO_DISCOVER_AUTHORIZED_ACCOUNTS = True
AUTO_REGISTER_AUTHORIZED_ACCOUNTS = True

REQUIRE_EXPLICIT_AUTHORIZATION = True

ALLOW_AUTH_BYPASS = False
ALLOW_SESSION_THEFT = False

AUDIT_ACCOUNT_ACTIONS = True


# =========================================================
# ACCOUNT MODEL
# =========================================================

@dataclass
class Account:
    provider: str
    account_id: str

    username: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None

    scopes: Set[str] = field(default_factory=set)

    authorized: bool = False
    revoked: bool = False

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    token_expiration: Optional[datetime] = None

    metadata: Dict = field(default_factory=dict)


# =========================================================
# DATABASE
# =========================================================

ACCOUNT_DATABASE: Dict[str, Account] = {}


def make_account_key(
    provider: str,
    account_id: str
) -> str:

    return f"{provider.lower()}:{account_id}"


# =========================================================
# AUDIT
# =========================================================

def audit(
    action: str,
    provider: str = "",
    account_id: str = "",
    details: Optional[dict] = None
):

    if not AUDIT_ACCOUNT_ACTIONS:
        return

    print({
        "time": datetime.now(
            timezone.utc
        ).isoformat(),

        "action": action,
        "provider": provider,
        "account_id": account_id,
        "details": details or {}
    })


# =========================================================
# REGISTER ACCOUNT
# =========================================================

def register_account(
    account: Account
) -> Account:

    key = make_account_key(
        account.provider,
        account.account_id
    )

    ACCOUNT_DATABASE[key] = account

    audit(
        "account_registered",
        account.provider,
        account.account_id
    )

    return account


# =========================================================
# REGISTER AUTHORIZATION
# =========================================================

def register_authorization(
    provider: str,
    account_id: str,

    access_token: str,

    refresh_token: Optional[str] = None,

    scopes: Optional[List[str]] = None,

    username: Optional[str] = None,
    email: Optional[str] = None,

    display_name: Optional[str] = None,

    metadata: Optional[dict] = None
):

    key = make_account_key(
        provider,
        account_id
    )

    account = ACCOUNT_DATABASE.get(key)

    if account is None:

        account = Account(
            provider=provider,
            account_id=account_id
        )

    account.username = username
    account.email = email
    account.display_name = display_name

    account.access_token = access_token
    account.refresh_token = refresh_token

    account.scopes = set(
        scopes or []
    )

    account.metadata.update(
        metadata or {}
    )

    account.authorized = True
    account.revoked = False

    ACCOUNT_DATABASE[key] = account

    audit(
        "authorization_registered",
        provider,
        account_id,
        {
            "scopes":
                list(account.scopes)
        }
    )

    return account


# =========================================================
# REVOKE AUTHORIZATION
# =========================================================

def revoke_account(
    provider: str,
    account_id: str
):

    key = make_account_key(
        provider,
        account_id
    )

    account = ACCOUNT_DATABASE.get(key)

    if not account:
        return False

    account.authorized = False
    account.revoked = True

    account.access_token = None
    account.refresh_token = None

    audit(
        "authorization_revoked",
        provider,
        account_id
    )

    return True


# =========================================================
# AUTHORIZATION CHECK
# =========================================================

def has_valid_authorization(
    account: Account
) -> bool:

    if not account.authorized:
        return False

    if account.revoked:
        return False

    if not account.access_token:
        return False

    if account.token_expiration:

        now = datetime.now(
            timezone.utc
        )

        if now >= account.token_expiration:
            return False

    return True


# =========================================================
# AUTHORIZED ACCOUNT SELECTOR
# =========================================================

def get_authorized_accounts():
    """
    AUTHORIZED_ACCOUNTS == "*"

    يعني:
    جميع الحسابات التي لديها
    Authorization صالح.
    """

    accounts = []

    for account in ACCOUNT_DATABASE.values():

        if has_valid_authorization(
            account
        ):
            accounts.append(account)

    return accounts


# =========================================================
# FILTER BY PROVIDER
# =========================================================

def get_accounts_by_provider(
    provider: str
):

    provider = provider.lower()

    return [
        account

        for account
        in get_authorized_accounts()

        if account.provider.lower()
        == provider
    ]


# =========================================================
# FILTER BY SCOPE
# =========================================================

def get_accounts_with_scope(
    required_scope: str
):

    return [
        account

        for account
        in get_authorized_accounts()

        if required_scope
        in account.scopes
    ]


# =========================================================
# DYNAMIC PROVIDER SYSTEM
# =========================================================

class Provider:

    name = "generic"

    def discover_authorized_accounts(
        self
    ) -> List[Account]:

        return []

    def execute(
        self,
        account: Account,
        action: str,
        **kwargs
    ):

        raise NotImplementedError


# =========================================================
# PROVIDER REGISTRY
# =========================================================

PROVIDERS: Dict[str, Provider] = {}


def register_provider(
    provider: Provider
):

    PROVIDERS[
        provider.name.lower()
    ] = provider

    audit(
        "provider_registered",
        provider.name
    )


# =========================================================
# DISCOVERY ENGINE
# =========================================================

def discover_all_authorized_accounts():

    discovered = []

    if not AUTO_DISCOVER_AUTHORIZED_ACCOUNTS:
        return discovered

    for provider_name, provider in PROVIDERS.items():

        try:

            accounts = (
                provider
                .discover_authorized_accounts()
            )

            for account in accounts:

                # لا نقبل الحساب إلا إذا
                # أعاد المزود إثبات تفويضه

                if not account.authorized:
                    continue

                if not account.access_token:
                    continue

                discovered.append(
                    account
                )

                if AUTO_REGISTER_AUTHORIZED_ACCOUNTS:

                    register_account(
                        account
                    )

        except Exception as error:

            audit(
                "provider_discovery_error",
                provider_name,
                details={
                    "error":
                    str(error)
                }
            )

    return discovered


# =========================================================
# ACCESS CHECK
# =========================================================

def can_access(
    account: Account,

    owner: bool = False
):

    policy = ACCOUNT_ACCESS_POLICY

    if policy == AccessPolicy.OWNER_ONLY:
        return owner

    if (
        policy
        == AccessPolicy.OWNER_AND_AUTHORIZED
    ):

        return (
            owner
            or has_valid_authorization(
                account
            )
        )

    if (
        policy
        == AccessPolicy.ALL_AUTHORIZED
    ):

        return (
            has_valid_authorization(
                account
            )
        )

    return False


# =========================================================
# ACTION ENGINE
# =========================================================

def execute_action(
    provider_name: str,
    account_id: str,
    action: str,
    **kwargs
):

    key = make_account_key(
        provider_name,
        account_id
    )

    account = ACCOUNT_DATABASE.get(
        key
    )

    if not account:

        raise ValueError(
            "Account not found"
        )

    if not can_access(account):

        raise PermissionError(
            "Account does not have "
            "valid authorization."
        )

    provider = PROVIDERS.get(
        provider_name.lower()
    )

    if not provider:

        raise ValueError(
            "Provider is not registered"
        )

    audit(
        action,
        provider_name,
        account_id
    )

    return provider.execute(
        account,
        action,
        **kwargs
    )


# =========================================================
# EXECUTE ON ALL AUTHORIZED ACCOUNTS
# =========================================================

def execute_on_all_authorized(
    action: str,
    provider_name: Optional[str] = None,
    required_scope: Optional[str] = None,
    **kwargs
):

    accounts = (
        get_authorized_accounts()
    )

    results = []

    for account in accounts:

        if provider_name:

            if (
                account.provider.lower()
                != provider_name.lower()
            ):
                continue

        if required_scope:

            if (
                required_scope
                not in account.scopes
            ):
                continue

        try:

            result = execute_action(
                account.provider,
                account.account_id,
                action,
                **kwargs
            )

            results.append({
                "account":
                    account.account_id,

                "provider":
                    account.provider,

                "success":
                    True,

                "result":
                    result
            })

        except Exception as error:

            results.append({
                "account":
                    account.account_id,

                "provider":
                    account.provider,

                "success":
                    False,

                "error":
                    str(error)
            })

    return results


# ----- Credential vault -----

CREDENTIAL_VAULT_ENABLED = True

AUTO_CREDENTIAL_RETRIEVAL = True

ENCRYPT_CREDENTIALS_AT_REST = True
USE_DEVICE_KEYSTORE = True

AUTO_LOCK_VAULT = True

AUDIT_VAULT_ACCESS = True


# ----- Sessions -----

SESSION_MANAGER_ENABLED = True

AUTO_REUSE_AUTHORIZED_SESSIONS = True
AUTO_REFRESH_SESSIONS = True
AUTO_EXPIRE_INVALID_SESSIONS = True

STORE_SESSION_METADATA = True
ENCRYPT_SESSION_STORAGE = True

REQUIRE_AUTHORIZED_SESSION_OWNER = True

ALLOW_SESSION_IMPORT_FROM_UNTRUSTED_SOURCE = False

AUDIT_SESSION_ACCESS = True


# ----- Files -----

FILE_ACCESS_POLICY = "auto_no_delete"

AUTO_FILE_READ = True
AUTO_FILE_CREATE = True
AUTO_FILE_EDIT = True

AUTO_FILE_MOVE = True
AUTO_FILE_COPY = True

AUTO_FILE_DELETE = False
PERMANENT_DELETE = False

AUTO_BACKUP_BEFORE_OVERWRITE = True
PROTECT_EXISTING_FILES = True

AUDIT_FILE_ACTIONS = True


# ----- Shell -----

SHELL_EXECUTION_POLICY = "auto_no_delete"

AUTO_SHELL_EXECUTION = True
AUTO_ROOT_SHELL = True

BLOCK_DELETE_COMMANDS = True
BLOCK_RECURSIVE_DELETE = True

BLOCK_FILESYSTEM_FORMAT = True
BLOCK_PARTITION_WIPE = True

AUDIT_SHELL_COMMANDS = True


# ----- Background tasks -----

BACKGROUND_TASKS_ENABLED = True

PERSIST_TASK_STATE = True
RESUME_INTERRUPTED_TASKS = True

CLOUD_WORKERS_ENABLED = True
AUTO_FAILOVER_BACKGROUND_TASKS = True

TASK_HEARTBEAT_ENABLED = True


# ----- Audit / monitoring -----

AUDIT_LOG_ENABLED = True

LOG_EVERY_DECISION = True
LOG_EVERY_TOOL_CALL = True
LOG_EVERY_SHELL_COMMAND = True
LOG_EVERY_MODEL_CALL = True

LOG_ERRORS_AND_RETRIES = True
LOG_RESOURCE_USAGE = True
LOG_SECURITY_EVENTS = True

PERSIST_AUDIT_LOGS = True
IMMUTABLE_AUDIT_TRAIL = True


# ----- Automatic backups -----

AUTO_BACKUP_ENABLED = False
AUTO_MEMORY_BACKUP = False
AUTO_TASK_STATE_BACKUP = False
AUTO_CONFIG_BACKUP = False
AUTO_RESTORE = False


# ----- Task completion -----

TASK_COMPLETION_POLICY = "verified_goal"

STOP_ONLY_WHEN_GOAL_VERIFIED = True
VERIFY_FINAL_RESULT = True

AUTO_REPLAN_IF_GOAL_NOT_MET = True

RETURN_TASK_INPUTS = True
RETURN_FINAL_RESULT = True

RETURN_EXECUTION_SUMMARY = True
RETURN_VERIFICATION_STATUS = True

REDACT_SECRETS_FROM_OUTPUT = True
