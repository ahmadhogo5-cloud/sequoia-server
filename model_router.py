Sequoia/
│
├── android-app/
│   ├── launcher/
│   ├── chat-ui/
│   ├── voice-ui/
│   ├── vision-ui/
│   ├── notifications/
│   ├── accessibility-service/
│   ├── device-bridge/
│   ├── root-bridge/
│   └── local-vault/
│
├── server/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── verifier.py
│   │   ├── recovery.py
│   │   └── context_manager.py
│   │
│   ├── models/
│   │   ├── model_router.py
│   │   ├── gemini_provider.py
│   │   ├── local_model.py
│   │   ├── self_hosted_model.py
│   │   ├── embedding_model.py
│   │   └── model_health.py
│   │
│   ├── memory/
│   │   ├── conversation_memory.py
│   │   ├── semantic_memory.py
│   │   ├── episodic_memory.py
│   │   ├── knowledge_memory.py
│   │   ├── people_memory.py
│   │   ├── relationship_graph.py
│   │   ├── memory_search.py
│   │   ├── memory_ranking.py
│   │   └── memory_cleanup.py
│   │
│   ├── tools/
│   │   ├── registry.py
│   │   │
│   │   ├── device/
│   │   │   ├── apps.py
│   │   │   ├── screen.py
│   │   │   ├── input.py
│   │   │   ├── notifications.py
│   │   │   ├── files.py
│   │   │   └── system.py
│   │   │
│   │   ├── browser/
│   │   │   ├── navigation.py
│   │   │   ├── forms.py
│   │   │   └── extraction.py
│   │   │
│   │   ├── web/
│   │   │   ├── search.py
│   │   │   ├── fetch.py
│   │   │   └── research.py
│   │   │
│   │   ├── files/
│   │   │   ├── reader.py
│   │   │   ├── writer.py
│   │   │   ├── pdf.py
│   │   │   └── archive.py
│   │   │
│   │   ├── code/
│   │   │   ├── python_runner.py
│   │   │   ├── compiler.py
│   │   │   └── sandbox_runner.py
│   │   │
│   │   ├── auth/
│   │   │   ├── credential_vault.py
│   │   │   ├── oauth.py
│   │   │   ├── passkeys.py
│   │   │   ├── totp.py
│   │   │   └── session_manager.py
│   │   │
│   │   └── security_lab/
│   │       ├── password_audit.py
│   │       ├── hash_lab.py
│   │       ├── mfa_lab.py
│   │       ├── session_lab.py
│   │       ├── web_lab.py
│   │       └── network_lab.py
│   │
│   ├── intelligence/
│   │   ├── intent_detection.py
│   │   ├── reasoning.py
│   │   ├── task_decomposition.py
│   │   ├── hypothesis_engine.py
│   │   ├── prediction.py
│   │   └── self_evaluation.py
│   │
│   ├── people/
│   │   ├── profiles.py
│   │   ├── interaction_history.py
│   │   ├── behavior_patterns.py
│   │   └── relationship_graph.py
│   │
│   ├── research/
│   │   ├── researcher.py
│   │   ├── source_collector.py
│   │   ├── evidence_checker.py
│   │   ├── hypothesis_generator.py
│   │   └── report_builder.py
│   │
│   ├── permissions/
│   │   ├── permissions.py
│   │   ├── target_authorization.py
│   │   ├── confirmation.py
│   │   └── capability_policy.py
│   │
│   ├── security/
│   │   ├── encryption.py
│   │   ├── secrets.py
│   │   ├── audit_log.py
│   │   ├── rate_limits.py
│   │   └── sandbox.py
│   │
│   ├── automation/
│   │   ├── scheduler.py
│   │   ├── workflows.py
│   │   ├── triggers.py
│   │   └── task_queue.py
│   │
│   └── api/
│       ├── chat.py
│       ├── memory.py
│       ├── tools.py
│       ├── device.py
│       ├── research.py
│       └── admin.py
│
├── database/
│   ├── postgres/
│   ├── pgvector/
│   ├── migrations/
│   └── backups/
│
├── sandbox/
│   ├── python/
│   ├── browser/
│   └── security-lab/
│
└── monitoring/
    ├── logs/
    ├── metrics/
    ├── tool-history/
    ├── model-history/
    └── error-recovery/
