# Security Policy

We take the security of GrugThink seriously. If you discover a security vulnerability, please report it responsibly so we can address it promptly.

## Reporting Security Vulnerabilities

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing the project maintainers directly or using GitHub's private security advisory feature.

## Vulnerability Report Guidelines

When reporting a security vulnerability, please include:

*   **Location:** Which component or file contains the vulnerability
*   **Description:** Clear explanation of the vulnerability and potential impact
*   **Reproduction Steps:** Step-by-step instructions to reproduce the issue
*   **Proof of Concept:** If possible, provide a minimal example demonstrating the vulnerability
*   **Suggested Fix:** If you have ideas for remediation, please include them

## Security Response Process

Our security response process:

1.  **Acknowledgment:** We will acknowledge receipt of your report within 48 hours
2.  **Assessment:** We will assess the vulnerability and determine its severity
3.  **Fix Development:** We will develop and test a fix for the vulnerability
4.  **Disclosure:** We will coordinate disclosure with you and provide credit if desired

## Security Considerations in GrugThink

### Data Protection
- **User Privacy**: User IDs are logged instead of usernames to protect privacy
- **Content Security**: Message content lengths are logged instead of actual content
- **Token Security**: All API tokens and secrets must be stored in environment variables

### Bot Security
- **Permission Isolation**: Each Discord server maintains isolated personality and fact databases
- **Rate Limiting**: Built-in rate limiting prevents abuse of verification commands
- **Input Validation**: All user inputs are validated and sanitized before processing

### Deployment Security
- **Environment Variables**: Sensitive configuration stored in .env files (never committed)
- **Docker Security**: Multi-stage builds minimize attack surface in production images
- **Dependencies**: Regular dependency updates to address known vulnerabilities

### API Security
- **Authentication**: Proper API key validation for Gemini and Google Search APIs
- **Network Security**: All external API calls use HTTPS encryption
- **Error Handling**: Error messages don't expose sensitive system information

## Security Updates

Security fixes will be released as soon as possible after confirmation. Critical vulnerabilities may result in emergency releases outside the normal release schedule.

Thank you for helping keep GrugThink secure! 🔒