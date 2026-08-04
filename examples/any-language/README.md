# Any-language remote runtime

A language needs only an HTTP, WebSocket, MQTT or gRPC client. The examples call
`POST /v1/convert` and therefore use the same server-side dialect registry and
diagnostics. Run the gateway on `http://localhost:8080` first.

| Language | Example | Dependencies |
|---|---|---|
| Bash/curl | `curl.sh` | curl |
| Go | `go/main.go` | Go standard library |
| Java | `java/Main.java` | Java 11+ standard library |
| C# | `csharp/Program.cs` | .NET standard library |
| PHP | `php/client.php` | PHP curl extension |
| Rust | `rust/` | `reqwest`, `serde_json` |
| JavaScript | `packages/js` | none in modern Node/browser |
| Python | `wellmanifest.client` | package or plain urllib firmware example |

For generated, typed RPC clients use
`proto/wellmanifest/v1/wellmanifest.proto` instead of hand-written HTTP.
