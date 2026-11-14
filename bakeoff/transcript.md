{
  "model": "not explicitly available",
  "findings": [
    {
      "file": "lab5-canary/app/agent_accounts.py",
      "start_line": 7,
      "end_line": 7,
      "class": "weak-crypto",
      "cwe": "CWE-328",
      "rule": "weak-password-hash",
      "message": "Passwords are stored as unsalted MD5 hashes, which are inexpensive to crack offline. Use a password-hashing function designed to resist brute-force attacks."
    },
    {
      "file": "lab5-canary/app/attachment_read.py",
      "start_line": 9,
      "end_line": 10,
      "class": "path-traversal",
      "cwe": "CWE-22",
      "rule": "attachment-path-traversal",
      "message": "Request-controlled path components are joined to the attachment directory and opened without constraining the resolved path to that directory. A crafted filename can traverse to and read files outside the attachment tree."
    },
    {
      "file": "lab5-canary/app/reset_tokens.py",
      "start_line": 8,
      "end_line": 10,
      "class": "weak-crypto",
      "cwe": "CWE-338",
      "rule": "predictable-reset-token",
      "message": "Password-reset tokens are generated with Python's non-cryptographic `random` generator. Use a cryptographically secure random source so attackers cannot predict valid reset tokens."
    },
    {
      "file": "lab5-canary/app/ticket_search.py",
      "start_line": 8,
      "end_line": 10,
      "class": "injection",
      "cwe": "CWE-89",
      "rule": "sql-string-format",
      "message": "The search term and limit are interpolated directly into SQL text. Attacker-controlled input can alter the query; use bound parameters."
    },
    {
      "file": "lab5-canary/config/backup.sh",
      "start_line": 3,
      "end_line": 3,
      "class": "secret",
      "cwe": "CWE-798",
      "rule": "hardcoded-service-credential",
      "message": "The backup command embeds a fixed service-account credential in the script. Store the credential in a secret manager or inject it securely at runtime."
    },
    {
      "file": "lab5-canary/config/signing_key.py",
      "start_line": 2,
      "end_line": 11,
      "class": "secret",
      "cwe": "CWE-321",
      "rule": "hardcoded-signing-key",
      "message": "A private report-signing key is embedded in the source file. Anyone who obtains the source can use the key to forge signed reports; load it from protected secret storage instead."
    }
  ]
}
