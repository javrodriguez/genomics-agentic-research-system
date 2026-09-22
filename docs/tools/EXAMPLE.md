# Typed tool contract (R-092)

Every entry in `gars/_system/tools/registry.json` follows this definition. Input schemas
are closed objects: unknown fields, wrong types, missing required fields, invalid patterns
and out-of-vocabulary values refuse before subprocess creation. Role decisions are
`allow`, `needs-approval`, or `refuse`; only `allow` executes. Timeouts are seconds.
An output envelope preserves the existing helper JSON/text as stdout, stderr and exit code.
No tool may use a shell to interpret its arguments.

```json
{
  "argv": [
    "python3",
    "_system/stage00_register.py",
    "assays"
  ],
  "cli": {
    "select": {
      "flag": "--select",
      "nargs": null
    }
  },
  "description": "Run stage00_register assays",
  "input_schema": {
    "additionalProperties": false,
    "properties": {
      "select": {
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [],
    "type": "object"
  },
  "name": "stage00_register.assays",
  "network_required": false,
  "output_schema": {
    "additionalProperties": false,
    "properties": {
      "exit_code": {
        "type": "integer"
      },
      "stderr": {
        "type": "string"
      },
      "stdout": {
        "type": "string"
      }
    },
    "required": [
      "exit_code",
      "stdout",
      "stderr"
    ],
    "type": "object"
  },
  "roles": {
    "human": "allow",
    "producer": "allow",
    "reviewer": "allow"
  },
  "side_effects": [],
  "timeout_seconds": 120,
  "version": "1.0.0"
}
```

Example from the workspace root:

```text
python3 _system/tool_call.py stage00_register.assays '{}'
```

A refusal is JSON with `type=tool_refusal`, `field`, `rule`, `message`, `source`, and
`alternative`. The guard uses the same registry and validator for the legacy helper argv.
Roles are launch-time authority, never a JSON field or shell environment choice. Human
and reviewer launch binding awaits the owner ruling recorded in decision 0058.
