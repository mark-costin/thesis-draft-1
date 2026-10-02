## Operational Rules & Status Codes

### Standard Error Envelope
All `4xx` and `5xx` responses must return this JSON structure:
```json
{
  "status": "error",
  "code": "VALIDATION_FAILED",
  "error": "Human-readable description of error.",
  "retryable": false
}