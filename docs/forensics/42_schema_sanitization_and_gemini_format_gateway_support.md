# Forensics Case 42: Tool Schema Sanitization and Gemini Wire Format Support

## 1. Executive Summary
- **Incident**: Testing model `cx/gpt-5.6-luna` (and other custom models via AIGateway / 9router) resulted in the planning engine aborting with:
  `[Error] Invalid schema for function 'send_message': "1" is not of type "integer"`
- **User Query**: Why does this occur, and can Gemini native wire format (`apiFormat: 'google'`) be used directly with gateways like 9router without lossy OpenAI translation?
- **Root Cause**:
  1. Google Antigravity's Language Server (`language_server_linux_x64`, implemented in Go) defines tool parameter schemas in Protobuf. Go's `protojson` marshaler serializes 64-bit integer constraint fields (`minLength`, `maxLength`, `minItems`, `maxItems`, `minProperties`, `maxProperties`) as JSON strings (e.g. `"minLength": "1"`).
  2. The custom model translator (`vendor/antigravity-model-proxy/dist/proxy/translators/openai.js` and `utils.js`) previously only lowercased `type: "STRING"` -> `type: "string"` and only inspected `properties`. It never coerced or cleaned numeric schema constraints.
  3. When forwarded to OpenAI-compatible gateways (such as LiteLLM, AIGateway, Ollama, 9router), JSON Schema validators (Draft 7 / 2020-12) strictly reject string numbers on integer keywords (`"1" is not of type "integer"`).
  4. Furthermore, gateways like 9router natively support Gemini wire format (`/v1beta/models/...:streamGenerateContent`), but upstream headers previously sent only `x-goog-api-key`, which some reverse proxies reject without `Authorization: Bearer`.
- **Resolution**:
  1. Implemented deep recursive JSON schema sanitization in `utils.js` (`fixParamTypes` & `sanitizeSchemaNode`) coercing all string integers (`minLength`, `maxLength`, `minItems`, `maxItems`, `minProperties`, `maxProperties`) and floats (`minimum`, `maximum`, `multipleOf`) into native numbers.
  2. Applied full schema sanitization across both `openai.js` and `anthropic.js` parameter definitions.
  3. Enabled dual authentication headers (`x-goog-api-key` and `Authorization: Bearer <key>`) when `apiFormat === 'google'` in `registry.js` and `modelManagement.js`.
  4. Updated `google.js` URL path construction using `encodeURI` to properly preserve namespace slashes for models such as `cx/gpt-5.6-luna`.
  5. Fixed Node.js event-loop hang in `shared.js` by unref'ing `cleanupInterval`.
  6. Re-packaged into `/opt/Antigravity-x64/resources/app.asar` preserving multi-patch coexistence (`RTL`, `F5`, `Selector`, `ModelPatch`). Added automated tests with 100% pass rate (216 tests).

---

## 2. Technical Root Cause Analysis

### 2.1 Protobuf `protojson` String Serialization
In Google's proto3 JSON mapping specification:
> "int64, fixed64, uint64 are serialized as string: e.g. '1'"
In Antigravity's tool definitions for `send_message`, `schedule`, `run_command`, parameters contain validation rules such as `minLength: 1` or `minProperties: 1`. When Go serializes them to JSON for RPC transport, they become:
```json
{
  "properties": {
    "Message": {
      "type": "STRING",
      "minLength": "1"
    },
    "Recipient": {
      "type": "STRING",
      "minLength": "1"
    }
  }
}
```

### 2.2 Strict JSON Schema Rejection
When `mapGeminiToolsToOpenAI` forwarded these schemas directly into `tools[].function.parameters`, downstream OpenAI-compatible API proxies (such as LiteLLM in AIGateway or 9router) validated the schema:
```python
# jsonschema validator:
# jsonschema.exceptions.ValidationError: '1' is not of type 'integer'
# Failed validating 'type' in schema['properties']['Message']['minLength']
```
This error was reflected directly to Antigravity as the model turn's error message.

---

## 3. Implementation Details

### 3.1 Recursive Schema Sanitization (`utils.js`)
In `vendor/antigravity-model-proxy/dist/proxy/translators/utils.js`:
- Added integer keyword coercion for:
  `['minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties']`.
- Added float keyword coercion for:
  `['minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf']`.
- Recurses through `properties`, `patternProperties`, `items`, `additionalProperties`, `anyOf`, `oneOf`, `allOf`, and `$defs`.
- Strips any invalid or unsupported keywords like `$schema`.

### 3.2 Dual Authentication for Gemini Format (`registry.js` & `modelManagement.js`)
When `apiFormat === 'google'`:
```javascript
headers['x-goog-api-key'] = apiKey;
headers.Authorization = `Bearer ${apiKey}`;
```
This guarantees interoperability with:
- Google AI Studio endpoints (`generativelanguage.googleapis.com`)
- Local & third-party AI routers (9router, LiteLLM, OneAPI, AIGateway)

### 3.3 Slashed Model Names in Gemini REST URL (`google.js`)
Changed `encodeURIComponent(chosenModel)` to `encodeURI(chosenModel)`.
- Models such as `cx/gpt-5.6-luna` route to `/v1beta/models/cx/gpt-5.6-luna:streamGenerateContent` rather than escaping the slash to `%2F` which causes HTTP 404 on routers with wildcard model subpath handlers.

---

## 4. Verification & Testing
1. **Node.js Wire Tests**:
   - `tests/test_models_wire_schema.py` verified tool schema coercion (`minLength: "1"` -> `1`, `minProperties: "1"` -> `1`).
   - Verified dual headers generation and URL formatting.
2. **Pytest Test Suite**:
   - Ran `pytest` across all suites: **216 passed** in 11.81s.
3. **App Asar Deployment**:
   - Ran `./manage-antigravity.sh patch-models --force`.
   - Verified all 4 active patches (`RTL`, `F5`, `Selector`, `ModelPatch`) remain intact.
