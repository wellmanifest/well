package main

import (
  "bytes"
  "encoding/json"
  "fmt"
  "io"
  "net/http"
  "os"
)

func main() {
  base := os.Getenv("WELLMANIFEST_URL")
  if base == "" { base = "http://localhost:8080" }
  request := map[string]any{
    "source": "status:\n  value: SUCCEEDED\n  errors: []\n",
    "source_dialect": "yaml",
    "target_dialect": "json",
    "projection": "data",
  }
  body, _ := json.Marshal(request)
  response, err := http.Post(base+"/v1/convert", "application/json", bytes.NewReader(body))
  if err != nil { panic(err) }
  defer response.Body.Close()
  output, _ := io.ReadAll(response.Body)
  if response.StatusCode >= 300 { panic(string(output)) }
  fmt.Println(string(output))
}
