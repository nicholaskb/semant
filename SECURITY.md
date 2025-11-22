# Security Policy

**Last Updated**: January 2025  
**Status**: Active

---

## Overview

This document outlines the security practices, policies, and procedures for the Semant multi-agent orchestration platform. All contributors and users are expected to follow these guidelines to maintain the security and integrity of the system.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, please report it privately:

### Reporting Process

1. **Email**: Send details to the security team (contact information in repository settings)
2. **Response Time**: We aim to acknowledge reports within **48 hours**
3. **Update Timeline**: We will provide updates every 7 days until resolution
4. **Disclosure Policy**: We will coordinate disclosure with the reporter after a fix is available

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested remediation (if any)

---

## Security Measures

### Authentication and Authorization

- **Environment Variables**: All API keys, tokens, and credentials are stored in `.env` files (gitignored)
- **No Hardcoded Secrets**: The codebase uses `config/settings.py` with Pydantic Settings to load from environment variables
- **Credential Management**: See `credentials/README.md` for detailed credential handling procedures

### Data Protection

- **Encryption**: All sensitive data in transit uses HTTPS/TLS
- **Storage**: Credentials stored locally in `.env` files (never committed to repository)
- **Knowledge Graph**: SPARQL endpoints support SSL verification (`KG_VERIFY_SSL` setting)

### Dependency Management

- **Requirements**: All dependencies are pinned in `requirements.txt`
- **Updates**: Regular dependency audits recommended (see Security Audit section)
- **Vulnerability Scanning**: Use tools like `pip-audit` or `safety` to check for known vulnerabilities

### Code Security

- **Gitignore Patterns**: Comprehensive `.gitignore` excludes:
  - `.env` and `.env.*` files
  - `credentials/*.json` and `credentials/token.pickle`
  - `__pycache__/` directories
  - Log files and temporary files

- **Settings Pattern**: Centralized configuration via `config/settings.py`:
  ```python
  # All settings loaded from .env, validated with Pydantic
  # No hardcoded values in production code
  ```

### CI/CD Security Controls

- **Pre-commit Hooks**: Recommended to set up `git-secrets` for pre-commit scanning (see Security Audit section)
- **Environment Variables**: CI/CD systems should use secure secret management (GitHub Secrets, GitLab CI Variables, etc.)

---

## Security Posture

### Current Status

✅ **No Hardcoded Secrets**: Verified via codebase scan (January 2025)  
✅ **Environment Variables**: All sensitive data uses `.env` pattern  
✅ **Gitignore**: Properly configured to exclude credentials  
✅ **Settings Validation**: Pydantic Settings enforce type safety and required fields  

### Security Audit Results

**Last Audit**: January 2025  
**Status**: CLEAN

**Findings**:
- ✅ No hardcoded API keys found in production code
- ✅ All secrets use environment variables
- ✅ Token-based authentication implemented
- ✅ `.env` file properly gitignored
- ✅ Credentials directory properly excluded from version control

**Test Files**: Some test files contain sandbox/demo keys (e.g., `tests/test_real_market_data.py`) - these are acceptable for testing purposes.

---

## Security Best Practices

### For Developers

1. **Never commit secrets**:
   ```bash
   # Always use .env files
   # Never commit: API keys, passwords, tokens, private keys
   ```

2. **Use environment variables**:
   ```python
   # ✅ GOOD: Load from environment
   from config.settings import settings
   api_key = settings.OPENAI_API_KEY
   
   # ❌ BAD: Hardcoded secret
   api_key = "sk-1234567890abcdef"
   ```

3. **Validate settings**:
   ```python
   # Settings are validated via Pydantic
   # Missing required fields will raise ValidationError
   ```

4. **Review .gitignore**:
   - Ensure new credential files are added to `.gitignore`
   - Verify sensitive directories are excluded

### For System Administrators

1. **Secure .env files**:
   - Set appropriate file permissions: `chmod 600 .env`
   - Restrict access to authorized users only
   - Use secure secret management in production (AWS Secrets Manager, HashiCorp Vault, etc.)

2. **Monitor access**:
   - Review audit logs regularly
   - Monitor for unauthorized access attempts
   - Rotate credentials periodically

3. **Network security**:
   - Use HTTPS for all API endpoints
   - Enable SSL verification for external connections
   - Implement rate limiting for API endpoints

---

## Security Audit Procedures

### Recommended Tools

1. **git-secrets** (AWS Labs):
   ```bash
   # Install
   git clone https://github.com/awslabs/git-secrets.git
   cd git-secrets && sudo make install
   
   # Configure
   git secrets --install
   git secrets --register-aws
   git secrets --add 'private_key|secret_key|password|token|api[_-]key'
   
   # Scan
   git secrets --scan -r .
   ```

2. **truffleHog**:
   ```bash
   # Install
   pip install truffleHog
   
   # Scan
   trufflehog --regex --entropy=True .
   ```

3. **pip-audit** (Python dependencies):
   ```bash
   pip install pip-audit
   pip-audit -r requirements.txt
   ```

### Audit Checklist

- [ ] Run `git-secrets` scan
- [ ] Run `truffleHog` scan
- [ ] Check for hardcoded secrets in code
- [ ] Verify `.gitignore` is comprehensive
- [ ] Review environment variable usage
- [ ] Audit dependencies for known vulnerabilities
- [ ] Review access controls and permissions
- [ ] Check SSL/TLS configuration
- [ ] Verify credential rotation procedures

---

## Known Limitations

1. **Local Development**: `.env` files are stored locally (not encrypted at rest)
2. **Credential Rotation**: Manual process - no automated rotation currently implemented
3. **Audit Logging**: Basic logging in place; comprehensive audit trail enhancement planned
4. **Pre-commit Hooks**: Not automatically installed - developers must set up manually

---

## Security Roadmap

### Planned Improvements

- [ ] Automated dependency vulnerability scanning in CI/CD
- [ ] Pre-commit hook automation for secret detection
- [ ] Enhanced audit logging with structured logs
- [ ] Automated credential rotation for service accounts
- [ ] Security scanning integration (Snyk, Dependabot, etc.)
- [ ] OWASP Top 10 compliance review
- [ ] Penetration testing for production deployments

---

## Additional Resources

- **Credential Management**: See `credentials/README.md`
- **Environment Setup**: See `QUICKSTART.md` and `docs/guides/env_setup_instructions.md`
- **Configuration**: See `config/settings.py` for settings pattern
- **Developer Guide**: See `docs/developer_guide.md` for development practices

---

## Contact

For security-related questions or concerns, please refer to the reporting process above or contact the maintainers through the repository's contact methods.

---

**Remember**: Security is everyone's responsibility. When in doubt, err on the side of caution and ask for guidance.

